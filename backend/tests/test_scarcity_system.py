import pytest
from uuid import uuid4

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
from backend.systems.scarcity_system import ScarcityEngine

class MockDB:
    async def commit(self):
        pass

@pytest.fixture
def scarcity_engine():
    return ScarcityEngine()

@pytest.fixture
def db():
    return MockDB()

@pytest.mark.asyncio
async def test_scarcity_blocks_unaffordable_action(scarcity_engine, db):
    project_id = uuid4()
    
    # State: 1000 resource_1 available. EXPAND needs 2000.
    state = GlobalEconomyState(project_id=project_id, resource_1_supply=1000.0, resource_2_supply=50000.0)
    
    # Mock economy getter
    async def _mock_get(session, pid):
        return state
    scarcity_engine._get_economy_state = _mock_get

    is_blocked, penalty, reason = await scarcity_engine.evaluate_action(
        db, project_id, ActionType.EXPAND_BUSINESS.value
    )
    
    assert is_blocked is True
    assert penalty == 0.0
    assert "Global resource_1 shortage" in reason

@pytest.mark.asyncio
async def test_scarcity_penalizes_strained_resources(scarcity_engine, db):
    project_id = uuid4()
    
    # Cost is 2000. Threshold is 6000 (3x). We have 4000.
    # We are 50% strained, so penalty should be 0.4 * 0.5 = 0.2
    state = GlobalEconomyState(project_id=project_id, resource_1_supply=4000.0, resource_2_supply=50000.0)
    
    async def _mock_get(session, pid):
        return state
    scarcity_engine._get_economy_state = _mock_get

    is_blocked, penalty, reason = await scarcity_engine.evaluate_action(
        db, project_id, ActionType.EXPAND_BUSINESS.value
    )
    
    assert is_blocked is False
    assert penalty > 0.1
    assert penalty < 0.3
    assert "Strained resource_1" in reason

@pytest.mark.asyncio
async def test_scarcity_passes_abundant_resources(scarcity_engine, db):
    project_id = uuid4()
    
    # 10000 compute > 6000 threshold. Should pass easily.
    state = GlobalEconomyState(project_id=project_id, resource_1_supply=10000.0, resource_2_supply=50000.0)
    
    async def _mock_get(session, pid):
        return state
    scarcity_engine._get_economy_state = _mock_get

    is_blocked, penalty, reason = await scarcity_engine.evaluate_action(
        db, project_id, ActionType.EXPAND_BUSINESS.value
    )
    
    assert is_blocked is False
    assert penalty == 0.0
    assert reason == ""

@pytest.mark.asyncio
async def test_scarcity_ignores_free_actions(scarcity_engine, db):
    project_id = uuid4()
    state = GlobalEconomyState(project_id=project_id, resource_1_supply=0.0, resource_2_supply=0.0)
    
    async def _mock_get(session, pid):
        return state
    scarcity_engine._get_economy_state = _mock_get

    # LOBBY_INFLUENCERS has no hardcoded requirements
    is_blocked, penalty, reason = await scarcity_engine.evaluate_action(
        db, project_id, ActionType.LOBBY_INFLUENCERS.value
    )
    
    assert is_blocked is False
    assert penalty == 0.0
