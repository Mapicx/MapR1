import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from backend.models.agent_models import Agent, MutablePsychology
from backend.models.action_models import AgentDecision, ActionExecutionResult
from backend.models.world_models import WorldState, StructuredWorldState
from backend.simulation.action_executor_v2 import ActionExecutorV2
from backend.simulation.contextual_consequence_engine import ContextualConsequenceEngine, ConsequenceContext, ACTION_FAMILY_SUCCESS_OUTCOMES

def create_decision(action_type: str, target_id: str) -> AgentDecision:
    return AgentDecision(
        action_type=action_type,
        action=action_type,
        target_id=target_id,
        justification="Test",
        reasoning="Test reasoning",
        confidence=0.8,
        expected_outcome="Test outcome",
        intel_shares=[]
    )

@pytest.fixture
def db_session():
    return AsyncMock()

@pytest.fixture
def mock_agent():
    agent = Agent(
        id=uuid4(),
        name="ActorCorp",
        agent_type="corporate",
        role="CEO",
        project_id=uuid4(),
        mutable_psychology=MutablePsychology(ego=0.5, paranoia=0.3, fear=0.2).model_dump()
    )
    return agent

@pytest.fixture
def mock_target():
    return Agent(
        id=uuid4(),
        name="TargetCorp",
        agent_type="corporate",
        role="CEO",
        project_id=uuid4()
    )

@pytest.fixture
def world_state():
    ws = WorldState(id=uuid4(), project_id=uuid4())
    structured = StructuredWorldState()
    ws.state = structured.to_dict()
    return ws

@pytest.fixture
def executor():
    return ActionExecutorV2()


@pytest.mark.asyncio
async def test_same_success_action_different_contexts(executor, db_session, mock_agent, mock_target, world_state):
    """Test that the same successful action produces different outcomes under different contexts."""
    
    # Mock resolve target
    executor._resolve_target_agent = AsyncMock(return_value=mock_target)
    
    decision = create_decision("sabotage", str(mock_target.id))
    
    with patch.object(ContextualConsequenceEngine, 'build_context') as mock_build_context, \
         patch.object(ContextualConsequenceEngine, 'resolve_success') as mock_resolve_success, \
         patch.object(ContextualConsequenceEngine, 'apply_secondary_effects') as mock_apply:
         
        # Simulate Context 1: Low Ego, High Paranoia
        ctx1 = ConsequenceContext(ego=0.1, paranoia=0.9)
        mock_build_context.return_value = ctx1
        
        mock_outcome1 = MagicMock()
        mock_outcome1.key = "hidden_retaliation_planned"
        mock_resolve_success.return_value = (mock_outcome1, "Outcome 1")
        
        res1 = await executor.execute_sabotage(db_session, mock_agent, decision, world_state, 1, True)
        assert res1.success is True
        assert "Outcome 1" in res1.outcome
        
        # Simulate Context 2
        ctx2 = ConsequenceContext(ego=0.9, paranoia=0.1)
        mock_build_context.return_value = ctx2
        mock_outcome2 = MagicMock()
        mock_outcome2.key = "ego_inflation"
        mock_resolve_success.return_value = (mock_outcome2, "Outcome 2")
        
        res2 = await executor.execute_sabotage(db_session, mock_agent, decision, world_state, 2, True)
        assert res2.success is True
        assert "Outcome 2" in res2.outcome


@pytest.mark.asyncio
async def test_contextual_engine_success_weights():
    """Test that the engine actually weights successes differently based on context."""
    engine = ContextualConsequenceEngine()
    
    # Context 1: High Ego
    ctx1 = ConsequenceContext(ego=1.0, actor_visibility=0.1, global_scarcity=0.1, world_instability=0.1)
    outcome1, _ = engine.resolve_success("hostile_takeover", MagicMock(name="Agent"), MagicMock(name="Target"), ctx1)
    
    # Context 2: High Scarcity
    ctx2 = ConsequenceContext(ego=0.1, actor_visibility=0.1, global_scarcity=1.0, world_instability=0.1)
    outcome2, _ = engine.resolve_success("hostile_takeover", MagicMock(name="Agent"), MagicMock(name="Target"), ctx2)
    
    assert outcome1.key in [o.key for o in ACTION_FAMILY_SUCCESS_OUTCOMES["hostile_takeover"]]


@pytest.mark.asyncio
async def test_psychology_mutates_after_major_win(executor, db_session, mock_agent, mock_target, world_state):
    """Test that success can mutate psychology."""
    
    engine = ContextualConsequenceEngine()
    structured = StructuredWorldState()
    
    # Force a specific outcome that mutates ego
    outcome = next(o for o in ACTION_FAMILY_SUCCESS_OUTCOMES["hostile_takeover"] if o.key == "ego_inflation")
    assert outcome.actor_ego_delta > 0
    
    initial_ego = mock_agent.mutable_psychology["ego"]
    
    await engine.apply_secondary_effects(
        db_session, mock_agent, mock_target, outcome, structured, 1, world_state
    )
    
    # Agent psychology should be updated
    assert mock_agent.mutable_psychology["ego"] > initial_ego
    assert db_session.add.called


@pytest.mark.asyncio
async def test_exploit_vulnerability_meaningful_risk(executor, db_session, mock_agent, mock_target, world_state):
    """Test that exploit_vulnerability failure now applies real consequences."""
    executor._resolve_target_agent = AsyncMock(return_value=mock_target)
    decision = create_decision("exploit_vulnerability", str(mock_target.id))
    
    with patch("backend.simulation.action_executor_v2.RelationshipManager") as mock_rel, \
         patch("backend.simulation.action_executor_v2.AgentMemoryManager") as mock_mem:
        
        mock_rel.return_value.record_interaction = AsyncMock()
        mock_mem.return_value.remember = AsyncMock()
        
        res = await executor.execute_exploit_vulnerability(db_session, mock_agent, decision, world_state, 1, False)
        
        assert res.success is False
        assert res.impact["exposure"] > 0
        assert res.impact["resources"] < 0
        assert res.impact["reputation"] < 0
        
        structured = StructuredWorldState.from_dict(world_state.state)
        assert len(structured.rivalries) == 1
        assert structured.rivalries[0].cause == "failed_exploit_attempt"
        
        assert mock_rel.return_value.record_interaction.called
        assert mock_mem.return_value.remember.called


@pytest.mark.asyncio
async def test_talent_deduplication(executor, db_session, mock_agent, mock_target, world_state):
    """Test that execute_poach_talent redirects to execute_talent."""
    decision = create_decision("poach_talent", str(mock_target.id))
    
    with patch.object(executor, 'execute_talent') as mock_exec_talent:
        mock_exec_talent.return_value = ActionExecutionResult(success=True, outcome="Mocked", impact={})
        
        res = await executor.execute_poach_talent(db_session, mock_agent, decision, world_state, 1, True)
        
        assert mock_exec_talent.called
        assert res.outcome == "Mocked"


@pytest.mark.asyncio
async def test_delayed_retaliation_scheduled(db_session, mock_agent, mock_target, world_state):
    """Test that delayed effects can be scheduled from a successful action."""
    engine = ContextualConsequenceEngine()
    structured = StructuredWorldState()
    
    # Find an outcome with a delayed effect
    outcome = next(o for o in ACTION_FAMILY_SUCCESS_OUTCOMES["attack"] if o.key == "alliance_retaliation_triggered")
    assert outcome.delayed_effect is not None
    
    with patch("backend.systems.delayed_effect_system.DelayedEffectSystem") as mock_delayed:
        mock_delayed.return_value.schedule = AsyncMock()
        
        await engine.apply_secondary_effects(
            db_session, mock_agent, mock_target, outcome, structured, 1, world_state
        )
        
        assert mock_delayed.return_value.schedule.called
        call_kwargs = mock_delayed.return_value.schedule.call_args.kwargs
        assert call_kwargs["event_type"] == outcome.delayed_effect["event_type"]
        assert call_kwargs["trigger_turn"] == 1 + outcome.delayed_effect.get("delay_turns", 2)
