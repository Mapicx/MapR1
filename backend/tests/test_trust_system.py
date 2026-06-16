import pytest
from uuid import uuid4
from unittest.mock import AsyncMock

from backend.models.db_models import Base
from backend.models.entity_models import Entity
from backend.models.timeline_models import Timeline
from backend.models.world_models import WorldState, StructuredWorldState
from backend.models.agent_models import Agent
from backend.models.goal_models import Goal
from backend.models.relationship_models import AgentRelationship
from backend.models.action_models import ActionType
from backend.models.delayed_effects import ScheduledEvent
from backend.models.economy_models import GlobalEconomyState
from backend.models.belief_models import PublicBeliefState, AgentBeliefState

from backend.systems.trust_system import TrustMisinformationSystem

class MockDB:
    def __init__(self):
        self.states = []
        
    def add(self, obj):
        self.states.append(obj)
        
    async def commit(self):
        pass
        
    async def get(self, *args, **kwargs):
        return None


@pytest.fixture
def trust_system():
    return TrustMisinformationSystem()

@pytest.fixture
def db():
    return MockDB()

@pytest.fixture
def source_agent():
    return Agent(id=uuid4(), name="Source", project_id=uuid4())


@pytest.mark.asyncio
async def test_spread_public_belief(trust_system, db, source_agent):
    project_id = source_agent.project_id
    
    # Mock source agent's state
    source_state = AgentBeliefState(
        agent_id=source_agent.id,
        propaganda_power=0.8,
        credibility=0.9
    )
    
    public_state = PublicBeliefState(
        project_id=project_id,
        beliefs={"The sky is green": 0.1} # Mostly disbelieved
    )
    
    async def _mock_get_agent(session, aid):
        return source_state
        
    async def _mock_get_public(session, pid):
        return public_state
        
    trust_system._get_or_create_agent_state = _mock_get_agent
    trust_system._get_or_create_public_state = _mock_get_public
    
    await trust_system.spread_belief(
        db, project_id, source_agent, "The sky is green", target_confidence=1.0, visibility=1.0
    )
    
    # Power = 0.8 * 0.9 * 1.0 = 0.72
    # Shift = (1.0 - 0.1) * 0.72 = 0.9 * 0.72 = 0.648
    # New conf = 0.1 + 0.648 = 0.748
    
    new_beliefs = public_state.beliefs
    assert "The sky is green" in new_beliefs
    assert new_beliefs["The sky is green"] == pytest.approx(0.748)
    # Belief diverged from truth (truth is sky is blue, but public believes it's green)


@pytest.mark.asyncio
async def test_spread_agent_belief(trust_system, db, source_agent):
    project_id = source_agent.project_id
    target_id = uuid4()
    
    source_state = AgentBeliefState(
        agent_id=source_agent.id,
        propaganda_power=1.0,
        credibility=1.0
    )
    
    # Target trusts source completely (1.0), but has high paranoia (0.8 in psychology, default 0.3 if missing)
    target_state = AgentBeliefState(
        agent_id=target_id,
        trust_in_others={str(source_agent.id): 1.0},
        known_facts={"Source is a spy": {"confidence": 0.5, "source": "hearsay", "step_learned": 1}}
    )
    
    async def _mock_get_agent(session, aid):
        if aid == source_agent.id:
            return source_state
        return target_state
        
    trust_system._get_or_create_agent_state = _mock_get_agent
    
    # Mock db get to return the mock agent
    # We create a dummy Agent with paranoia=0.8
    mock_agent = Agent(id=target_id, mutable_psychology={"paranoia": 0.8})
    db.get = AsyncMock(return_value=mock_agent)
    
    await trust_system.spread_belief(
        db, project_id, source_agent, "Source is a spy", target_confidence=0.0, target_agent_id=target_id
    )
    
    # Effective Power = 1.0 * 1.0 (trust) * (1.0 - 0.8 paranoia) = 0.2
    # New Confidence = 0.5 + 0.2 * (0.0 - 0.5) = 0.4
    
    new_facts = target_state.known_facts
    assert new_facts["Source is a spy"]["confidence"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_get_beliefs(trust_system, db, source_agent):
    project_id = source_agent.project_id
    
    public_state = PublicBeliefState(project_id=project_id, beliefs={"Water is wet": 0.99})
    agent_state = AgentBeliefState(agent_id=source_agent.id, known_facts={"Water is dry": {"confidence": 0.8, "source": "rumor", "step_learned": 1}})
    
    async def _mock_get_agent(session, aid):
        return agent_state
        
    async def _mock_get_public(session, pid):
        return public_state
        
    trust_system._get_or_create_agent_state = _mock_get_agent
    trust_system._get_or_create_public_state = _mock_get_public
    
    public = await trust_system.get_public_beliefs(db, project_id)
    agent_b = await trust_system.get_agent_beliefs(db, source_agent.id)
    
    assert public["Water is wet"] == 0.99
    assert agent_b["Water is dry"]["confidence"] == 0.8
