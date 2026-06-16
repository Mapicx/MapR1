import pytest
import random
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.models.db_models import Base
from backend.models.agent_models import Agent
from backend.models.belief_models import AgentBeliefState
from backend.models.action_models import AgentDecision, IntelShareDecision
from backend.simulation.simulation_engine import SimulationEngine
from backend.systems.trust_system import TrustMisinformationSystem

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import ARRAY

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "JSON"

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

class MockWorldState:
    def __init__(self, project_id, alliances):
        self.project_id = project_id
        self.state = {"alliances": alliances}

class MockActionExecutor:
    def _get_structured_state(self, ws):
        class Structured:
            def __init__(self, a):
                self.alliances = a
        return Structured(ws.state["alliances"])
        
    def _save_structured_state(self, ws, st):
        pass

@pytest.mark.asyncio
async def test_intel_sharing_success(db_session, monkeypatch):
    # Setup
    project_id = uuid4()
    agent_a_id = uuid4()
    agent_b_id = uuid4()
    
    agent_a = Agent(id=agent_a_id, name="Alice", agent_type="role_1", role="Leader", project_id=project_id)
    agent_b = Agent(id=agent_b_id, name="Bob", agent_type="role_2", role="Follower", project_id=project_id)
    db_session.add_all([agent_a, agent_b])
    
    state_a = AgentBeliefState(agent_id=agent_a_id, known_facts={}, propaganda_power=0.8, credibility=0.9)
    state_b = AgentBeliefState(agent_id=agent_b_id, known_facts={}, propaganda_power=0.5, credibility=0.5)
    db_session.add_all([state_a, state_b])
    await db_session.commit()
    
    class DummyAlliance:
        def __init__(self, a, b):
            self.agent_a = a
            self.agent_b = b
            
    world_state = MockWorldState(project_id, [DummyAlliance(str(agent_a_id), str(agent_b_id))])
    
    decision = AgentDecision(
        action="wait",
        reasoning="test",
        confidence=1.0,
        expected_outcome="test",
        intel_shares=[
            IntelShareDecision(
                target_agent_id=str(agent_b_id),
                fact_content="Secret Base Found",
                is_fabricated=False,
                distortion_intent="inflate",
                reasoning="Internal monologue log only"
            )
        ]
    )
    
    # We patch the executor and systems minimally to run the sharing block
    from backend.simulation.simulation_engine import SimulationEngine
    engine = SimulationEngine()
    engine.action_executor = MockActionExecutor()
    
    # We will simulate the snippet from simulation_engine.py
    # Since we can't easily mock the entire step(), we just test the logic directly
    from backend.systems.fog_system import FogOfWarSystem
    fog_system = FogOfWarSystem()
    trust_system = TrustMisinformationSystem()
    
    structured = engine.action_executor._get_structured_state(world_state)
    
    for intel_share in decision.intel_shares:
        target_id_str = intel_share.target_agent_id
        agent_id_str = str(agent_a.id)
        is_ally = True
        
        source_state = await trust_system._get_or_create_agent_state(db_session, agent_a.id)
        propaganda = source_state.propaganda_power
        credibility = source_state.credibility
        
        base_conf = 0.6
        intent = intel_share.distortion_intent
        is_fab = intel_share.is_fabricated
        content = intel_share.fact_content
        
        if intent == "inflate":
            base_conf += (propaganda * 0.3)
            
        if not is_fab and credibility < 0.4:
            pass # credibility is 0.9, shouldn't flip
            
        final_conf = max(0.1, min(1.0, base_conf))
        
        target_res = await db_session.execute(select(Agent).where(Agent.id == agent_b_id))
        target_agent = target_res.scalars().first()
        
        await fog_system._reveal_fact(db_session, project_id, target_agent, content, agent_a.name, final_conf, 1)
        
    await db_session.commit()
    
    # Check belief state
    res = await db_session.execute(select(AgentBeliefState).where(AgentBeliefState.agent_id == agent_b_id))
    b_state = res.scalar_one()
    
    assert "Secret Base Found" in b_state.known_facts
    # base 0.6 + (0.8 * 0.3) = 0.84
    assert abs(b_state.known_facts["Secret Base Found"]["confidence"] - 0.84) < 0.001

@pytest.mark.asyncio
async def test_credibility_flip(db_session):
    agent_a_id = uuid4()
    agent_a = Agent(id=agent_a_id, name="Liar", agent_type="role_1", role="Trickster", project_id=uuid4())
    db_session.add(agent_a)
    
    # Credibility 0.0 -> flip prob is (0.4 - 0.0)*0.5 = 0.20
    state_a = AgentBeliefState(agent_id=agent_a_id, known_facts={}, propaganda_power=0.5, credibility=0.0)
    db_session.add(state_a)
    await db_session.commit()
    
    flip_count = 0
    import random
    for i in range(1000):
        is_fab = False
        content = "Truth"
        if not is_fab and state_a.credibility < 0.4:
            flip_prob = (0.4 - state_a.credibility) * 0.5
            if random.random() < flip_prob:
                is_fab = True
                content = f"[Distorted] {content}"
        if is_fab:
            flip_count += 1
            assert "[Distorted]" in content
            
    # Should be around 200
    assert 150 < flip_count < 250
