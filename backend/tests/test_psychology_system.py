import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
from unittest.mock import AsyncMock

from backend.models.agent_models import Agent, MutablePsychology
from backend.models.world_models import StructuredWorldState
from backend.models.action_models import ActionExecutionResult
from backend.systems.psychology_system import PsychologySystem

@pytest.fixture
def agent():
    return Agent(
        id=uuid4(),
        name="TestAgent",
        agent_type="ceo",
        role="Test Role",
        mutable_psychology=MutablePsychology().model_dump()
    )

@pytest.fixture
def structured_world():
    return StructuredWorldState()

@pytest.fixture
def psychology_system():
    return PsychologySystem()

@pytest.fixture
def db_session_mock():
    # Just need a mock for db.add
    return AsyncMock(spec=AsyncSession)

@pytest.mark.asyncio
async def test_repeated_failure_mutates_psychology(agent, structured_world, psychology_system, db_session_mock):
    # Initial state
    assert agent.mutable_psychology.get("consecutive_failures", 0) == 0
    assert agent.mutable_psychology.get("radicalization", 0.1) == 0.1
    
    # Fail 1
    fail_result = ActionExecutionResult(success=False, outcome="Failed")
    await psychology_system.update_agent_psychology(db_session_mock, agent, "expand business", fail_result, structured_world)
    assert agent.mutable_psychology["consecutive_failures"] == 1
    assert agent.mutable_psychology["fear"] > 0.2
    
    # Fail 2
    await psychology_system.update_agent_psychology(db_session_mock, agent, "expand business", fail_result, structured_world)
    assert agent.mutable_psychology["consecutive_failures"] == 2
    
    # Fail 3 -> Radicalization
    await psychology_system.update_agent_psychology(db_session_mock, agent, "expand business", fail_result, structured_world)
    assert agent.mutable_psychology["consecutive_failures"] == 3
    assert agent.mutable_psychology["radicalization"] > 0.1
    assert agent.mutable_psychology["paranoia"] > 0.3

@pytest.mark.asyncio
async def test_success_resets_failures(agent, structured_world, psychology_system, db_session_mock):
    agent.mutable_psychology["consecutive_failures"] = 2
    
    success_result = ActionExecutionResult(success=True, outcome="Success")
    await psychology_system.update_agent_psychology(db_session_mock, agent, "expand business", success_result, structured_world)
    
    assert agent.mutable_psychology["consecutive_failures"] == 0
    assert agent.mutable_psychology["ego"] > 0.5
    assert agent.mutable_psychology["fear"] < 0.2

@pytest.mark.asyncio
async def test_scarcity_changes_psychology(agent, structured_world, psychology_system, db_session_mock):
    # Set resources low
    structured_world.agent_resources[str(agent.id)] = 0.2
    
    success_result = ActionExecutionResult(success=True, outcome="Success")
    await psychology_system.update_agent_psychology(db_session_mock, agent, "wait", success_result, structured_world)
    
    assert agent.mutable_psychology["greed"] > 0.5
    assert agent.mutable_psychology["desperation"] > 0.0

@pytest.mark.asyncio
async def test_betrayal_changes_psychology(agent, structured_world, psychology_system, db_session_mock):
    success_result = ActionExecutionResult(success=True, outcome="Success")
    await psychology_system.update_agent_psychology(db_session_mock, agent, "betrayal", success_result, structured_world)
    
    assert agent.mutable_psychology["idealism"] < 0.5
    assert agent.mutable_psychology["risk_tolerance"] > 0.5
    assert agent.mutable_psychology["paranoia"] > 0.3
