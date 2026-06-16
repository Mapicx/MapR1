import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.agent_models import Agent
from backend.models.action_models import AgentDecision
from backend.models.world_models import WorldState
from backend.agents.decision_engine import DecisionEngine
from backend.simulation.action_executor_v2 import ActionExecutorV2

async def test_proposals():
    # Setup mocks
    db = AsyncMock(spec=AsyncSession)
    
    # Agents
    agent_a = Agent(id=uuid4(), name="Elena (CEO)", agent_type="ceo", role="Business Leader", personality={"rationality": 0.9})
    agent_b = Agent(id=uuid4(), name="Dr. Arav (Diplomat)", agent_type="diplomacy", role="Chief Negotiator", personality={"trusting": 0.8})
    
    # Engines
    decision_engine = DecisionEngine()
    # Mock candidate generator and other things that hit DB inside make_decision
    decision_engine._load_discoveries = AsyncMock(return_value=[])
    
    action_executor = ActionExecutorV2()
    action_executor._resolve_target_agent = AsyncMock(return_value=agent_b)
    
    # Initialize World State
    world_state = WorldState(id=uuid4(), state={
        "agent_resources": {}, "agent_power": {}, "agent_reputation": {}, 
        "agent_exposure": {}, "recent_events": [], "pending_proposals": []
    })
    
    print("=========================================")
    print("TESTING ASYNC PROPOSALS")
    print("=========================================\n")
    
    # 1. Agent A Proposes an Alliance
    print(f"STEP 1: {agent_a.name} executes 'form alliance'")
    decision_a = AgentDecision(
        action="form alliance", reasoning="I need Arav's help to secure the market.",
        confidence=0.9, expected_outcome="Arav agrees", risks=[], affected_agents=[str(agent_b.id)]
    )
    result_a = await action_executor.execute_action(db, agent_a, decision_a, world_state, simulation_step=1, success=True)
    
    print(f"Outcome: {result_a.outcome}")
    structured = action_executor._get_structured_state(world_state)
    print(f"Pending Proposals in World State: {len(structured.pending_proposals)}")
    print(f"Proposal Data: {structured.pending_proposals[0]['context']}")
    print("-" * 40)
    
    # 2. Agent B receives the proposal in its decision prompt
    print(f"STEP 2: Generating decision for {agent_b.name}...")
    
    import backend.simulation.action_executor_v2
    class MockCooldownManager:
        def __init__(self, *args, **kwargs): pass
        async def get_recent_actions(self, *args, **kwargs): return []
        def apply_cooldowns(self, candidates, *args, **kwargs): return candidates
    backend.agents.decision_engine.ActionCooldownManager = MockCooldownManager
    class MockRelManager:
        def __init__(self, *args, **kwargs): pass
        async def record_interaction(self, *args, **kwargs): pass
        async def get_all_relationships(self, *args, **kwargs): return []
        async def get_relationship_context(self, *args, **kwargs): return "No prior relationship."
    backend.agents.decision_engine.RelationshipManager = MockRelManager
    
    class MockGoalManager:
        def __init__(self, *args, **kwargs): pass
        async def get_active_goals(self, *args, **kwargs): return []
        async def get_goal_context(self, *args, **kwargs): return "Goal: maintain peace."
    backend.agents.decision_engine.GoalManager = MockGoalManager
    
    class MockMemoryManager:
        def __init__(self, *args, **kwargs): pass
        async def build_context(self, *args, **kwargs): return "Memory: Normal day."
        async def remember(self, *args, **kwargs): pass
    backend.agents.decision_engine.AgentMemoryManager = MockMemoryManager
    
    decision_b = await decision_engine.make_decision(
        db, agent=agent_b, situation="It is a quiet morning.", available_actions=["research", "wait", "negotiate"], current_step=2, world_state=world_state
    )
    
    print(f"LLM Main Action: {decision_b.action}")
    print(f"LLM Reasoning: {decision_b.reasoning}")
    print(f"LLM Proposal Responses: {decision_b.proposal_responses}")
    print("-" * 40)
    
    # 3. Simulation Engine processes the response
    print("STEP 3: Simulation Engine Resolves Responses")
    
    from backend.models.world_models import AllianceRecord, WorldEventRecord
    
    proposals_to_remove = []
    for prop_id, response in decision_b.proposal_responses.items():
        print(f"Processing response for {prop_id}: {response}")
        proposal = next((p for p in structured.pending_proposals if p.get("id") == prop_id), None)
        if proposal:
            target_id_str = proposal.get("from_agent_id")
            prop_type = proposal.get("type")
            
            if response.lower() == "accept":
                if prop_type in ["alliance", "coalition"]:
                    structured.alliances.append(AllianceRecord(
                        agent_a=str(agent_b.id), agent_b=target_id_str,
                        formed_at_step=2, strength=0.5, alliance_type="strategic"
                    ))
                    structured.agent_power[str(agent_b.id)] = 0.65
                    print("--> Alliance Formed! Power increased.")
            else:
                print("--> Proposal Rejected! Trust decreased.")
                
            proposals_to_remove.append(proposal)
            
    for p in proposals_to_remove:
        if p in structured.pending_proposals:
            structured.pending_proposals.remove(p)
            
    print(f"Final Pending Proposals: {len(structured.pending_proposals)}")
    print(f"Total Alliances: {len(structured.alliances)}")

if __name__ == "__main__":
    asyncio.run(test_proposals())
