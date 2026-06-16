import pytest
from uuid import uuid4

from backend.models.belief_models import AgentBeliefState
from backend.models.agent_models import Agent
from backend.systems.fog_system import FogOfWarSystem

class MockDB:
    def __init__(self):
        self.states = []
        
    def add(self, obj):
        self.states.append(obj)
        
    async def commit(self):
        pass

@pytest.fixture
def fog_system():
    return FogOfWarSystem()

@pytest.fixture
def db():
    return MockDB()

@pytest.mark.asyncio
async def test_broadcast_event_direct_experience(fog_system, db):
    project_id = uuid4()
    agent = Agent(id=uuid4(), name="Alice", project_id=project_id)
    state = AgentBeliefState(agent_id=agent.id, known_facts={})
    
    async def _mock_get_agent(session, aid):
        return state
        
    fog_system._get_or_create_agent_state = _mock_get_agent
    
    # Alice did the action, so she should know it with 1.0 confidence
    await fog_system.broadcast_event(
        db, project_id, actor_name="Alice", target_name=None, outcome="Alice hacked the mainframe",
        base_visibility=0.1, actor_exposure=0.1, all_agents=[agent], current_step=5
    )
    
    facts = state.known_facts
    assert "Alice hacked the mainframe" in facts
    assert facts["Alice hacked the mainframe"]["confidence"] == 1.0
    assert facts["Alice hacked the mainframe"]["source"] == "direct_experience"
    assert facts["Alice hacked the mainframe"]["step_learned"] == 5

@pytest.mark.asyncio
async def test_broadcast_event_observation(fog_system, db, monkeypatch):
    project_id = uuid4()
    actor = Agent(id=uuid4(), name="Alice", project_id=project_id)
    observer = Agent(id=uuid4(), name="Bob", project_id=project_id)
    state = AgentBeliefState(agent_id=observer.id, known_facts={})
    
    async def _mock_get_agent(session, aid):
        return state
        
    fog_system._get_or_create_agent_state = _mock_get_agent
    
    # Force random to return 0.0 so it always passes the check
    import random
    monkeypatch.setattr(random, "random", lambda: 0.0)
    
    # High visibility, high exposure = (0.8 + 0.8) / 2 = 0.8 obviousness
    await fog_system.broadcast_event(
        db, project_id, actor_name="Alice", target_name=None, outcome="Alice gave a speech",
        base_visibility=0.8, actor_exposure=0.8, all_agents=[actor, observer], current_step=10
    )
    
    facts = state.known_facts
    assert "Alice gave a speech" in facts
    assert facts["Alice gave a speech"]["confidence"] == 1.0 # obviousness(0.8) + 0.2 = 1.0
    assert facts["Alice gave a speech"]["source"] == "observation"
    assert facts["Alice gave a speech"]["step_learned"] == 10

@pytest.mark.asyncio
async def test_broadcast_event_hidden(fog_system, db, monkeypatch):
    project_id = uuid4()
    observer = Agent(id=uuid4(), name="Bob", project_id=project_id)
    state = AgentBeliefState(agent_id=observer.id, known_facts={})
    
    async def _mock_get_agent(session, aid):
        return state
        
    fog_system._get_or_create_agent_state = _mock_get_agent
    
    # Force random to return 0.9 (fails the check since obviousness is low)
    import random
    monkeypatch.setattr(random, "random", lambda: 0.9)
    
    # Low visibility = (0.1 + 0.1) / 2 = 0.1 obviousness
    await fog_system.broadcast_event(
        db, project_id, actor_name="Alice", target_name=None, outcome="Alice whispered a secret",
        base_visibility=0.1, actor_exposure=0.1, all_agents=[observer], current_step=12
    )
    
    facts = state.known_facts
    # Bob should not know this
    assert "Alice whispered a secret" not in facts
