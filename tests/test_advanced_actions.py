import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock


from backend.simulation.action_executor_v2 import ActionExecutorV2
from backend.models.agent_models import Agent
from backend.agents.decision_engine import AgentDecision
from backend.models.world_models import WorldState

async def test_actions():
    executor = ActionExecutorV2()
    
    # Mock _resolve_target_agent to return a dummy agent without hitting the DB
    dummy_target = Agent(id=uuid4(), name="TestTargetCompany")
    executor._resolve_target_agent = AsyncMock(return_value=dummy_target)
    
    # Mock RelationshipManager
    import backend.simulation.action_executor_v2
    class MockRelManager:
        def __init__(self, *args, **kwargs):
            pass
        async def record_interaction(self, *args, **kwargs):
            pass
    backend.simulation.action_executor_v2.RelationshipManager = MockRelManager
    
    # Dummy WorldState
    world_state = WorldState(id=uuid4(), state={"agent_resources": {}, "agent_power": {}, "agent_reputation": {}, "agent_exposure": {}, "recent_events": []})
    
    actor = Agent(id=uuid4(), name="TestActor")
    db = AsyncMock()

    actions_to_test = [
        "bid on contract",
        "lobby influencers",
        "file legal action",
        "media campaign",
        "hostile takeover",
        "poach talent",
        "exploit vulnerability",
        "form coalition",
        "leak secrets",
        "defensive restructuring"
    ]
    
    print("=========================================")
    print("🧪 TESTING ADVANCED ACTION ROUTING & LOGIC")
    print("=========================================\n")
    
    for action_str in actions_to_test:
        decision = AgentDecision(
            action=action_str,
            reasoning="Testing",
            confidence=0.9,
            expected_outcome="Success",
            risks=[],
            affected_agents=[]
        )
        
        # Test Success
        res_success = await executor.execute_action(db, actor, decision, world_state, 1, True)
        
        # Test Failure
        res_failure = await executor.execute_action(db, actor, decision, world_state, 1, False)
        
        print(f"[{action_str.upper()}]")
        print(f"  ✅ SUCCESS: {res_success.outcome}")
        print(f"     Impact: {res_success.impact}")
        print(f"  ❌ FAILURE: {res_failure.outcome}")
        print(f"     Impact: {res_failure.impact}")
        print("-" * 40)
        
if __name__ == "__main__":
    asyncio.run(test_actions())
