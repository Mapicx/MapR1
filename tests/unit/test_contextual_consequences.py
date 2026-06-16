"""
Tests for the Contextual Consequence Engine.

Proves:
1. Same action produces different outcomes under different contexts
2. Visibility changes exposure likelihood
3. Scarcity changes betrayal/resource-drain likelihood
4. Paranoia changes retaliation probability
5. Consequences persist across later turns (memory + world state)
"""

import sys
import random
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Ensure the project root is in the path
sys.path.insert(0, ".")

from backend.simulation.contextual_consequence_engine import (
    ConsequenceContext,
    ContextualConsequenceEngine,
    _compute_weight_multipliers,
    SABOTAGE_FAILURE_OUTCOMES,
    POLICY_FAILURE_OUTCOMES,
    BETRAYAL_FAILURE_OUTCOMES,
    LEAK_FAILURE_OUTCOMES,
    ACTION_FAMILY_OUTCOMES,
)
from backend.models.agent_models import MutablePsychology


# ============================================================================
# Helpers
# ============================================================================


def make_agent(name="TestAgent", agent_id=None, psychology=None):
    """Create a mock Agent."""
    agent = MagicMock()
    agent.id = agent_id or uuid4()
    agent.name = name
    agent.project_id = uuid4()
    agent.mutable_psychology = (psychology or MutablePsychology()).model_dump()
    return agent


def make_structured_world(**overrides):
    """Create a mock StructuredWorldState."""
    from backend.models.world_models import StructuredWorldState
    return StructuredWorldState(**overrides)


def default_context(**overrides) -> ConsequenceContext:
    """Create a ConsequenceContext with sensible defaults."""
    defaults = dict(
        paranoia=0.3,
        fear=0.2,
        ego=0.5,
        greed=0.5,
        desperation=0.0,
        radicalization=0.1,
        consecutive_failures=0,
        target_trust=0.5,
        relationship_strength=0.0,
        is_ally=False,
        is_rival=False,
        actor_visibility=0.5,
        actor_reputation=0.5,
        public_fear=0.0,
        actor_resources=0.5,
        target_resources=0.5,
        global_scarcity=0.0,
        recent_betrayals=0,
        recent_failures_total=0,
        world_instability=0.0,
        active_rivalries=0,
        active_alliances=0,
        actor_recent_actions=[],
    )
    defaults.update(overrides)
    return ConsequenceContext(**defaults)


# ============================================================================
# Test 1: Same action, different contexts → different outcomes
# ============================================================================


class TestContextualDivergence:
    """Prove that the same action family produces different outcomes
    when contexts differ."""

    def test_sabotage_produces_diverse_outcomes_across_contexts(self):
        """Run 200 resolutions under varied contexts and confirm
        we get at least 4 distinct outcome keys."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Attacker")
        target = make_agent("Victim")

        outcome_keys = set()
        contexts = [
            default_context(paranoia=0.9, actor_visibility=0.9),
            default_context(paranoia=0.1, actor_visibility=0.1),
            default_context(global_scarcity=0.9, desperation=0.8),
            default_context(ego=0.9, public_fear=0.8),
            default_context(is_ally=True, target_trust=0.9),
            default_context(consecutive_failures=5, fear=0.9),
        ]

        for ctx in contexts:
            for _ in range(40):
                outcome, desc = engine.resolve_failure("sabotage", agent, target, ctx)
                outcome_keys.add(outcome.key)

        assert len(outcome_keys) >= 4, (
            f"Expected at least 4 distinct sabotage outcomes, got {len(outcome_keys)}: {outcome_keys}"
        )

    def test_betrayal_produces_diverse_outcomes(self):
        """Betrayal family should also produce diverse outcomes."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Betrayer")
        target = make_agent("Victim")

        outcome_keys = set()
        contexts = [
            default_context(paranoia=0.9, actor_visibility=0.9, recent_betrayals=3),
            default_context(paranoia=0.1, actor_visibility=0.1),
            default_context(ego=0.9, public_fear=0.8),
            default_context(is_ally=True, target_trust=0.1),
        ]

        for ctx in contexts:
            for _ in range(50):
                outcome, desc = engine.resolve_failure("betrayal", agent, target, ctx)
                outcome_keys.add(outcome.key)

        assert len(outcome_keys) >= 4, (
            f"Expected at least 4 distinct betrayal outcomes, got {len(outcome_keys)}: {outcome_keys}"
        )

    def test_same_action_different_context_different_description(self):
        """Two different contexts for the same action should NOT always
        produce the same description string."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Actor")
        target = make_agent("Target")

        ctx_high_paranoia = default_context(paranoia=0.95, actor_visibility=0.9)
        ctx_low_paranoia = default_context(paranoia=0.05, actor_visibility=0.1)

        descriptions_high = set()
        descriptions_low = set()

        for _ in range(30):
            _, desc = engine.resolve_failure("sabotage", agent, target, ctx_high_paranoia)
            descriptions_high.add(desc)
            _, desc = engine.resolve_failure("sabotage", agent, target, ctx_low_paranoia)
            descriptions_low.add(desc)

        # At least one description should differ between high and low paranoia
        assert descriptions_high != descriptions_low or len(descriptions_high) > 1


# ============================================================================
# Test 2: Visibility changes exposure likelihood
# ============================================================================


class TestVisibilityEffect:
    """Prove that higher visibility makes exposure outcomes more likely."""

    def test_high_visibility_increases_exposure_outcomes(self):
        """Outcomes with actor_exposure_delta > 0 should be selected more
        often when actor_visibility is high."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("VisibleAgent")
        target = make_agent("Target")

        # Count exposure outcomes under high vs low visibility
        high_vis_exposure_count = 0
        low_vis_exposure_count = 0
        n_trials = 500

        ctx_high_vis = default_context(actor_visibility=0.95)
        ctx_low_vis = default_context(actor_visibility=0.05)

        for _ in range(n_trials):
            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_high_vis)
            if outcome.actor_exposure_delta > 0:
                high_vis_exposure_count += 1

            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_low_vis)
            if outcome.actor_exposure_delta > 0:
                low_vis_exposure_count += 1

        # High visibility should produce more exposure outcomes
        assert high_vis_exposure_count > low_vis_exposure_count, (
            f"High vis exposure ({high_vis_exposure_count}) should exceed "
            f"low vis exposure ({low_vis_exposure_count})"
        )

    def test_weight_multiplier_for_exposed_operative_increases_with_visibility(self):
        """The weight multiplier for 'exposed_operative' should be higher
        with high actor_visibility."""
        from backend.simulation.contextual_consequence_engine import SABOTAGE_FAILURE_OUTCOMES

        exposed_outcome = next(o for o in SABOTAGE_FAILURE_OUTCOMES if o.key == "exposed_operative")

        ctx_high = default_context(actor_visibility=0.9)
        ctx_low = default_context(actor_visibility=0.1)

        weight_high = _compute_weight_multipliers(exposed_outcome, ctx_high)
        weight_low = _compute_weight_multipliers(exposed_outcome, ctx_low)

        assert weight_high > weight_low, (
            f"High vis weight ({weight_high:.2f}) should exceed low vis weight ({weight_low:.2f})"
        )


# ============================================================================
# Test 3: Scarcity changes betrayal/resource-drain likelihood
# ============================================================================


class TestScarcityEffect:
    """Prove that scarcity amplifies resource-drain and desperation outcomes."""

    def test_scarcity_increases_resource_drain(self):
        """Under high scarcity, 'resource_drain' should be selected more often."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("ScarceAgent")
        target = make_agent("Target")

        resource_drain_high_scarcity = 0
        resource_drain_low_scarcity = 0
        n_trials = 500

        ctx_high = default_context(global_scarcity=0.9, actor_resources=0.1)
        ctx_low = default_context(global_scarcity=0.1, actor_resources=0.8)

        for _ in range(n_trials):
            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_high)
            if outcome.key == "resource_drain":
                resource_drain_high_scarcity += 1

            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_low)
            if outcome.key == "resource_drain":
                resource_drain_low_scarcity += 1

        assert resource_drain_high_scarcity > resource_drain_low_scarcity, (
            f"High scarcity resource_drain ({resource_drain_high_scarcity}) should exceed "
            f"low scarcity ({resource_drain_low_scarcity})"
        )

    def test_scarcity_amplifies_loyalty_collapse_in_betrayal(self):
        """Under high scarcity, 'loyalty_collapse' in betrayal should be more likely."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Betrayer")
        target = make_agent("Victim")

        loyalty_high = 0
        loyalty_low = 0
        n_trials = 500

        ctx_high = default_context(global_scarcity=0.9)
        ctx_low = default_context(global_scarcity=0.1)

        for _ in range(n_trials):
            outcome, _ = engine.resolve_failure("betrayal", agent, target, ctx_high)
            if outcome.key == "loyalty_collapse":
                loyalty_high += 1

            outcome, _ = engine.resolve_failure("betrayal", agent, target, ctx_low)
            if outcome.key == "loyalty_collapse":
                loyalty_low += 1

        assert loyalty_high > loyalty_low, (
            f"High scarcity loyalty_collapse ({loyalty_high}) should exceed low ({loyalty_low})"
        )


# ============================================================================
# Test 4: Paranoia changes retaliation probability
# ============================================================================


class TestParanoiaEffect:
    """Prove that high paranoia amplifies retaliation outcomes."""

    def test_paranoia_increases_retaliation(self):
        """High paranoia should make retaliation outcomes much more frequent."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("ParanoidAgent")
        target = make_agent("Target")

        retaliation_keys = {"retaliation_escalation", "retaliation_planning", "paranoia_spike"}

        retaliation_high_paranoia = 0
        retaliation_low_paranoia = 0
        n_trials = 500

        ctx_high = default_context(paranoia=0.95)
        ctx_low = default_context(paranoia=0.05)

        for _ in range(n_trials):
            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_high)
            if outcome.key in retaliation_keys:
                retaliation_high_paranoia += 1

            outcome, _ = engine.resolve_failure("sabotage", agent, target, ctx_low)
            if outcome.key in retaliation_keys:
                retaliation_low_paranoia += 1

        assert retaliation_high_paranoia > retaliation_low_paranoia, (
            f"High paranoia retaliation ({retaliation_high_paranoia}) should exceed "
            f"low paranoia ({retaliation_low_paranoia})"
        )

    def test_weight_multiplier_for_retaliation_increases_with_paranoia(self):
        """Direct unit test: the weight multiplier for retaliation_escalation
        should be higher with high paranoia."""
        retaliation_outcome = next(
            o for o in SABOTAGE_FAILURE_OUTCOMES if o.key == "retaliation_escalation"
        )

        ctx_high = default_context(paranoia=0.95)
        ctx_low = default_context(paranoia=0.1)

        weight_high = _compute_weight_multipliers(retaliation_outcome, ctx_high)
        weight_low = _compute_weight_multipliers(retaliation_outcome, ctx_low)

        assert weight_high > weight_low * 2.0, (
            f"High paranoia weight ({weight_high:.2f}) should be >2x "
            f"low paranoia weight ({weight_low:.2f})"
        )


# ============================================================================
# Test 5: Consequences persist (world state + psychology mutations)
# ============================================================================


class TestPersistentConsequences:
    """Prove that consequences mutate persistent state."""

    @patch("backend.simulation.contextual_consequence_engine.RelationshipManager")
    @patch("backend.simulation.contextual_consequence_engine.AgentMemoryManager")
    def test_outcome_mutates_psychology(self, mock_memory, mock_rel):
        """An outcome with paranoia_delta should actually change
        the agent's mutable_psychology."""
        mock_rel.return_value.record_interaction = AsyncMock()
        mock_memory.return_value.remember = AsyncMock()
        engine = ContextualConsequenceEngine()

        # Find an outcome that has actor_paranoia_delta > 0
        outcome = next(
            o for o in SABOTAGE_FAILURE_OUTCOMES if o.actor_paranoia_delta > 0
        )

        agent = make_agent("TestAgent", psychology=MutablePsychology(paranoia=0.3))
        target = make_agent("Target")
        structured = make_structured_world(
            agent_resources={str(agent.id): 0.5},
            agent_reputation={str(agent.id): 0.5},
            agent_exposure={str(agent.id): 0.0},
            agent_power={str(agent.id): 0.5},
        )

        # Mock db
        db = AsyncMock()
        db.add = MagicMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step=1
            )
        )

        # Check agent psychology was modified
        new_psych = MutablePsychology(**agent.mutable_psychology)
        expected_paranoia = 0.3 + outcome.actor_paranoia_delta
        assert abs(new_psych.paranoia - expected_paranoia) < 0.01, (
            f"Expected paranoia ~{expected_paranoia}, got {new_psych.paranoia}"
        )

    @patch("backend.simulation.contextual_consequence_engine.RelationshipManager")
    @patch("backend.simulation.contextual_consequence_engine.AgentMemoryManager")
    def test_outcome_mutates_world_state_reputation(self, mock_memory, mock_rel):
        """An outcome with actor_reputation_delta should change the
        agent's reputation in StructuredWorldState."""
        mock_rel.return_value.record_interaction = AsyncMock()
        mock_memory.return_value.remember = AsyncMock()
        engine = ContextualConsequenceEngine()

        outcome = next(
            o for o in SABOTAGE_FAILURE_OUTCOMES if o.actor_reputation_delta < 0
        )

        agent = make_agent("TestAgent")
        target = make_agent("Target")
        agent_id_str = str(agent.id)
        structured = make_structured_world(
            agent_resources={agent_id_str: 0.5},
            agent_reputation={agent_id_str: 0.7},
            agent_exposure={agent_id_str: 0.1},
            agent_power={agent_id_str: 0.5},
        )

        db = AsyncMock()
        db.add = MagicMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step=1
            )
        )

        expected_rep = max(0.0, 0.7 + outcome.actor_reputation_delta)
        actual_rep = structured.agent_reputation[agent_id_str]
        assert abs(actual_rep - expected_rep) < 0.01, (
            f"Expected reputation ~{expected_rep}, got {actual_rep}"
        )

    @patch("backend.simulation.contextual_consequence_engine.RelationshipManager")
    @patch("backend.simulation.contextual_consequence_engine.AgentMemoryManager")
    def test_outcome_creates_rivalry(self, mock_memory, mock_rel):
        """An outcome with creates_rivalry=True should add a rivalry
        to StructuredWorldState."""
        mock_rel.return_value.record_interaction = AsyncMock()
        mock_memory.return_value.remember = AsyncMock()
        engine = ContextualConsequenceEngine()

        outcome = next(
            o for o in SABOTAGE_FAILURE_OUTCOMES if o.creates_rivalry
        )

        agent = make_agent("Attacker")
        target = make_agent("Defender")
        structured = make_structured_world(
            agent_resources={str(agent.id): 0.5, str(target.id): 0.5},
            agent_reputation={str(agent.id): 0.5},
            agent_exposure={str(agent.id): 0.0},
            agent_power={str(agent.id): 0.5},
        )

        db = AsyncMock()
        db.add = MagicMock()

        assert len(structured.rivalries) == 0

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step=1
            )
        )

        assert len(structured.rivalries) >= 1, "A rivalry should have been created"
        rivalry = structured.rivalries[0]
        assert {rivalry.agent_a, rivalry.agent_b} == {str(agent.id), str(target.id)}

    @patch("backend.simulation.contextual_consequence_engine.RelationshipManager")
    @patch("backend.simulation.contextual_consequence_engine.AgentMemoryManager")
    def test_outcome_records_event(self, mock_memory, mock_rel):
        """Consequences should log a WorldEventRecord to recent_events."""
        mock_rel.return_value.record_interaction = AsyncMock()
        mock_memory.return_value.remember = AsyncMock()
        engine = ContextualConsequenceEngine()

        outcome = SABOTAGE_FAILURE_OUTCOMES[0]  # Any outcome

        agent = make_agent("Actor")
        target = make_agent("Target")
        structured = make_structured_world(
            agent_resources={str(agent.id): 0.5},
            agent_reputation={str(agent.id): 0.5},
            agent_exposure={str(agent.id): 0.0},
            agent_power={str(agent.id): 0.5},
        )

        initial_events = len(structured.recent_events)

        db = AsyncMock()
        db.add = MagicMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            engine.apply_secondary_effects(
                db, agent, target, outcome, structured, simulation_step=5
            )
        )

        assert len(structured.recent_events) > initial_events, (
            "At least one new event should have been recorded"
        )
        new_event = structured.recent_events[-1]
        assert new_event.step == 5
        assert new_event.actor == agent.name


# ============================================================================
# Test: Context building
# ============================================================================


class TestContextBuilding:
    """Test that ConsequenceContext is correctly built from world state."""

    def test_context_captures_psychology(self):
        """Psychology values should be reflected in the context."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Agent", psychology=MutablePsychology(
            paranoia=0.8, fear=0.6, ego=0.9
        ))
        structured = make_structured_world(
            agent_resources={str(agent.id): 0.3},
            agent_reputation={str(agent.id): 0.4},
            agent_exposure={str(agent.id): 0.7},
            agent_power={str(agent.id): 0.5},
        )

        db = AsyncMock()

        import asyncio
        ctx = asyncio.get_event_loop().run_until_complete(
            engine.build_context(db, agent, None, structured)
        )

        assert ctx.paranoia == 0.8
        assert ctx.fear == 0.6
        assert ctx.ego == 0.9
        assert ctx.actor_visibility == 0.7
        assert abs(ctx.actor_resources - 0.3) < 0.01

    def test_context_captures_scarcity(self):
        """Global scarcity should be computed from avg resources."""
        engine = ContextualConsequenceEngine()
        agent = make_agent("Agent")
        structured = make_structured_world(
            agent_resources={str(agent.id): 0.1, "other": 0.1},
            agent_reputation={str(agent.id): 0.5},
            agent_exposure={str(agent.id): 0.0},
            agent_power={str(agent.id): 0.5},
        )

        db = AsyncMock()

        import asyncio
        ctx = asyncio.get_event_loop().run_until_complete(
            engine.build_context(db, agent, None, structured)
        )

        # Average resources = 0.1, so scarcity = 1 - 0.1 = 0.9
        assert ctx.global_scarcity >= 0.8, f"Expected high scarcity, got {ctx.global_scarcity}"


# ============================================================================
# Test: Weight multiplier correctness
# ============================================================================


class TestWeightMultipliers:
    """Direct unit tests for the weight multiplier function."""

    def test_all_outcomes_have_positive_weights(self):
        """No outcome should ever have a zero or negative weight."""
        ctx = default_context()

        for family_name, outcomes in ACTION_FAMILY_OUTCOMES.items():
            for outcome in outcomes:
                weight = _compute_weight_multipliers(outcome, ctx)
                assert weight > 0, (
                    f"{family_name}/{outcome.key} has non-positive weight: {weight}"
                )

    def test_public_fear_amplifies_panic_outcomes(self):
        """High public fear should amplify public_panic weight in leak outcomes."""
        panic_outcome = next(
            o for o in LEAK_FAILURE_OUTCOMES if o.key == "public_panic"
        )

        ctx_high_fear = default_context(public_fear=0.9)
        ctx_low_fear = default_context(public_fear=0.1)

        weight_high = _compute_weight_multipliers(panic_outcome, ctx_high_fear)
        weight_low = _compute_weight_multipliers(panic_outcome, ctx_low_fear)

        assert weight_high > weight_low, (
            f"High fear weight ({weight_high:.2f}) should exceed low fear ({weight_low:.2f})"
        )

    def test_ally_betrayal_amplifies_rivalry_outcomes(self):
        """Betraying an ally should amplify outcomes that create rivalries."""
        for outcome in BETRAYAL_FAILURE_OUTCOMES:
            if outcome.creates_rivalry:
                ctx_ally = default_context(is_ally=True)
                ctx_non_ally = default_context(is_ally=False)

                weight_ally = _compute_weight_multipliers(outcome, ctx_ally)
                weight_non_ally = _compute_weight_multipliers(outcome, ctx_non_ally)

                assert weight_ally > weight_non_ally, (
                    f"Ally betrayal weight for {outcome.key} ({weight_ally:.2f}) should exceed "
                    f"non-ally ({weight_non_ally:.2f})"
                )
                break  # Only need to test one

    def test_consecutive_failures_amplify_desperation(self):
        """Multiple consecutive failures should amplify desperation outcomes."""
        desperation_outcome = next(
            o for o in SABOTAGE_FAILURE_OUTCOMES if o.actor_desperation_delta > 0
        )

        ctx_many_failures = default_context(consecutive_failures=4)
        ctx_no_failures = default_context(consecutive_failures=0)

        weight_high = _compute_weight_multipliers(desperation_outcome, ctx_many_failures)
        weight_low = _compute_weight_multipliers(desperation_outcome, ctx_no_failures)

        assert weight_high > weight_low, (
            f"Many failures weight ({weight_high:.2f}) should exceed "
            f"no failures ({weight_low:.2f})"
        )


# ============================================================================
# Test: Action family coverage
# ============================================================================


class TestActionFamilyCoverage:
    """Ensure all action families have reasonable outcome tables."""

    def test_all_families_have_outcomes(self):
        for family in ["sabotage", "policy", "betrayal", "leak"]:
            outcomes = ACTION_FAMILY_OUTCOMES[family]
            assert len(outcomes) >= 5, (
                f"Family '{family}' should have at least 5 outcomes, has {len(outcomes)}"
            )

    def test_all_outcomes_have_unique_keys(self):
        for family, outcomes in ACTION_FAMILY_OUTCOMES.items():
            keys = [o.key for o in outcomes]
            assert len(keys) == len(set(keys)), (
                f"Family '{family}' has duplicate keys: {keys}"
            )

    def test_all_outcomes_have_description_template(self):
        for family, outcomes in ACTION_FAMILY_OUTCOMES.items():
            for outcome in outcomes:
                assert "{actor}" in outcome.description_template, (
                    f"{family}/{outcome.key} missing {{actor}} in template"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
