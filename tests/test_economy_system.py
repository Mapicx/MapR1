
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.models.db_models import Base
from backend.models.entity_models import Entity
from backend.models.timeline_models import Timeline
from backend.models.world_models import WorldState, StructuredWorldState
from backend.models.agent_models import Agent
from backend.models.goal_models import Goal
from backend.models.relationship_models import AgentRelationship
from backend.models.action_models import AgentAction, ActionType
from backend.models.delayed_effects import ScheduledEvent
from backend.models.economy_models import GlobalEconomyState
from backend.systems.economy_system import EconomySystem

class MockDB:
    async def commit(self):
        pass

async def get_test_db():
    return MockDB()

async def test_economy_system_deterministic_costs():
    db = MockDB()
    project_id = uuid4()
    economy_sys = EconomySystem()
    
    # Mock _get_or_create
    state = GlobalEconomyState(
        project_id=project_id,
        resource_1_supply=100000.0,
        resource_2_supply=50000.0,
        resource_3_supply=7000.0,
        public_unemployment=0.12,
        gdp_growth=0.03,
        market_confidence=0.65,
        displaced_units=0
    )
    economy_sys._get_or_create = lambda d, pid: _mock_get(state)
    
    async def _mock_get(s):
        return s
    structured_world = StructuredWorldState()

    # Create dummy actions
    action1 = AgentAction(action_type=ActionType.EXPAND_BUSINESS.value, executed=True)
    action2 = AgentAction(action_type=ActionType.RESEARCH.value, executed=True)

    result = await economy_sys.update(db, project_id, [action1, action2], structured_world)

    economy = result["economy"]

    # Starting compute: 100000
    # EXPAND uses 2000, RESEARCH uses 3000
    # Natural regen: +1000
    # Total expected: 100000 - 5000 + 1000 = 96000
    assert economy["resource_1_supply"] == 96000

    # EXPAND adds 50000 units replaced
    assert economy["displaced_units"] == 50000

async def test_economy_scarcity_cascade():
    db = MockDB()
    project_id = uuid4()
    economy_sys = EconomySystem()
    
    # Mock _get_or_create
    state = GlobalEconomyState(
        project_id=project_id,
        resource_1_supply=100000.0,
        resource_2_supply=50000.0,
        resource_3_supply=7000.0,
        public_unemployment=0.12,
        gdp_growth=0.03,
        market_confidence=0.65,
        displaced_units=0
    )
    economy_sys._get_or_create = lambda d, pid: _mock_get(state)
    
    async def _mock_get(s):
        return s
    structured_world = StructuredWorldState()
    
    # We will simulate draining compute supply so it drops below 50000
    actions = []
    # EXPAND_BUSINESS uses 2000 compute. To drop below 50000 from 100000 we need 26 actions.
    for _ in range(26):
        actions.append(AgentAction(action_type=ActionType.EXPAND_BUSINESS.value, executed=True))

    result = await economy_sys.update(db, project_id, actions, structured_world)
    economy = result["economy"]

    # Initial compute: 100000
    # Cost: 26 * 2000 = 52000
    # Regen: +1000
    # Result: 49000
    assert economy["resource_1_supply"] == 49000

    # Because resource_1 dropped < 50000, resource_2 takes an extra 1000 hit
    # Initial energy: 50000
    # Cost (expand doesn't cost energy)
    # Scarcity cascade: -1000
    # Regen: +500
    # Expected: 50000 - 1000 + 500 = 49500
    assert economy["resource_2_supply"] == 49500

    # Unemployment cascade:
    # 26 expands * 50000 = 1.3M units replaced
    # Cascade: > 100,000 adds unemployment
    # 1.3M // 100k = 13 * 0.02 = +0.26
    # Initial: 0.12. Expected: 0.38
    assert abs(economy["public_unemployment"] - 0.38) < 0.001

async def test_economy_persistence():
    db = MockDB()
    project_id = uuid4()
    economy_sys = EconomySystem()
    
    # Mock _get_or_create
    state = GlobalEconomyState(
        project_id=project_id,
        resource_1_supply=100000.0,
        resource_2_supply=50000.0,
        resource_3_supply=7000.0,
        public_unemployment=0.12,
        gdp_growth=0.03,
        market_confidence=0.65,
        displaced_units=0
    )
    economy_sys._get_or_create = lambda d, pid: _mock_get(state)
    
    async def _mock_get(s):
        return s
    structured_world = StructuredWorldState()

    # Step 1
    action = AgentAction(action_type=ActionType.EXPAND_BUSINESS.value, executed=True)
    await economy_sys.update(db, project_id, [action], structured_world)

    # Step 2
    result = await economy_sys.update(db, project_id, [], structured_world)
    economy = result["economy"]

    # Step 1: 100000 - 2000 + 1000 = 99000
    # Step 2: 99000 - 0 + 1000 = 100000
    assert economy["resource_1_supply"] == 100000

    # Verify state is saved by loading it separately
    state = await economy_sys._get_or_create(db, project_id)
    assert state.resource_1_supply == 100000

if __name__ == "__main__":
    import asyncio
    
    async def run_all():
        print("Running tests...")
        
        print("1. test_economy_system_deterministic_costs")
        await test_economy_system_deterministic_costs()
        print("2. test_economy_scarcity_cascade")
        await test_economy_scarcity_cascade()
        print("3. test_economy_persistence")
        await test_economy_persistence()
            
        print("All tests passed!")

    asyncio.run(run_all())
