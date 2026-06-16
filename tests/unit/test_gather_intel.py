import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
import asyncio

from backend.models.db_models import Base
from backend.models.action_models import ActionType, AgentDecision
from backend.models.agent_models import Agent
from backend.models.goal_models import Goal, GoalStatus
from backend.models.belief_models import AgentBeliefState
from backend.systems.economy_system import EconomySystem
from backend.simulation.action_executor_v2 import ActionExecutorV2

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

@pytest.mark.asyncio
async def test_economy_costs():
    system = EconomySystem()
    costs = system.action_impacts
    assert costs["negotiate"] == {"resource_1": -200, "resource_2": -100}
    assert costs["file_legal_action"] == {"resource_1": -400, "confidence": -0.02}
    assert costs["spread_ideology"] == {"resource_1": -500, "resource_2": -300}
    assert costs["betray"] == {"resource_1": -200, "resource_2": -200}
    assert costs["seek_revenge"] == {"resource_1": -300, "resource_2": -200}
    assert costs["bid_on_contract"] == {"resource_1": -500, "resource_2": -200}

@pytest.mark.asyncio
async def test_gather_intel_action(db_session):
    agent_id = uuid4()
    project_id = uuid4()
    agent = Agent(id=agent_id, name="TestAgent", project_id=project_id, agent_type="role_1", role="Test Role")
    db_session.add(agent)
    
    goal_id = uuid4()
    goal = Goal(id=goal_id, agent_id=agent_id, description="Test Goal", goal_type="power", priority=1.0, status=GoalStatus.ACTIVE.value, knowledge_score=0.1)
    db_session.add(goal)
    await db_session.commit()
    
    from unittest.mock import patch

    executor = ActionExecutorV2()
    decision = AgentDecision(
        action="gather_intel",
        reasoning="Need info",
        confidence=0.8,
        expected_outcome="gain intel",
        intel_shares=[]
    )
    
    class MockWorldState:
        def __init__(self):
            self.project_id = project_id
            self.state = {"structured_state": {"agent_resources": {}, "agent_power": {}, "recent_events": []}}
            
    world_state = MockWorldState()
    
    with patch("backend.simulation.action_executor_v2.AgentMemoryManager.remember") as mock_remember:
        mock_remember.return_value = None
        result = await executor.execute_action(db_session, agent, decision, world_state, 1, True)
    
    assert result.success is True
    assert "knowledge_gain" in result.impact or "knowledge_score" in result.impact
    
    await db_session.refresh(goal)
    assert goal.knowledge_score > 0.1
    
    from sqlalchemy import select
    res = await db_session.execute(select(AgentBeliefState).where(AgentBeliefState.agent_id == agent_id))
    belief_state = res.scalar_one_or_none()
    
    assert belief_state is not None
    assert len(belief_state.known_facts) > 0
    fact_key = "Gathered vague intelligence at step 1"
    assert fact_key in belief_state.known_facts
    assert belief_state.known_facts[fact_key]["confidence"] == 0.5
    assert belief_state.known_facts[fact_key]["source"] == "direct_experience"
