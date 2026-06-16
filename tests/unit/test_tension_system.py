"""
Tests for the Mechanical Tension Feedback System.
"""

import sys
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Ensure the project root is in the path
sys.path.insert(0, ".")

from backend.systems.tension_modifier_system import (
    TensionModifierSystem,
    apply_tension_to_psychology_delta,
    apply_tension_to_trust_decay
)
from backend.simulation.contextual_consequence_engine import (
    ConsequenceContext,
    ContextualConsequenceEngine
)
from backend.models.agent_models import MutablePsychology


def default_context(**overrides) -> ConsequenceContext:
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
        tension=0.0,
    )
    defaults.update(overrides)
    return ConsequenceContext(**defaults)


def test_tension_modifiers_scale_nonlinearly():
    """Verify multipliers scale exponentially as tension rises."""
    low_mods = TensionModifierSystem.get_modifiers(0.1)
    high_mods = TensionModifierSystem.get_modifiers(0.9)
    
    assert high_mods.catastrophic_probability > low_mods.catastrophic_probability * 1.5
    assert high_mods.consequence_severity > low_mods.consequence_severity
    assert high_mods.action_volatility > low_mods.action_volatility
    assert high_mods.alliance_decay > low_mods.alliance_decay


def test_tension_increases_catastrophic_failure_probability():
    """Verify that high tension makes catastrophic outcomes far more frequent."""
    engine = ContextualConsequenceEngine()
    
    agent = MagicMock()
    agent.id = uuid4()
    agent.name = "Actor"
    agent.mutable_psychology = MutablePsychology().model_dump()
    
    target = MagicMock()
    target.id = uuid4()
    target.name = "Target"
    
    ctx_low = default_context(tension=0.0)
    ctx_high = default_context(tension=0.95)
    
    catastrophic_count_low = 0
    catastrophic_count_high = 0
    
    catastrophic_keys = {
        "exposed_operative", "retaliation_escalation", "public_backlash",
        "loyalty_collapse", "public_panic", "civilian_panic",
        "retaliation_planning", "market_panic", "public_scandal",
        "catastrophic_failure", "collapse"
    }

    n_trials = 500
    for _ in range(n_trials):
        out_low, _ = engine.resolve_failure("sabotage", agent, target, ctx_low)
        if out_low.key in catastrophic_keys:
            catastrophic_count_low += 1
            
        out_high, _ = engine.resolve_failure("sabotage", agent, target, ctx_high)
        if out_high.key in catastrophic_keys:
            catastrophic_count_high += 1

    assert catastrophic_count_high > catastrophic_count_low * 1.5, (
        f"High tension catastrophe count ({catastrophic_count_high}) should be "
        f"substantially higher than low tension ({catastrophic_count_low})"
    )


def test_psychology_delta_amplification():
    """Verify that psychology changes are amplified under tension."""
    delta = 0.1
    delta_low = apply_tension_to_psychology_delta(delta, tension=0.0)
    delta_high = apply_tension_to_psychology_delta(delta, tension=0.95)
    
    assert delta_high > delta_low * 1.5, "Psychology delta should amplify at high tension"


def test_trust_decay_accelerates_at_high_tension():
    """Verify that alliances and trust erode faster when tension is high."""
    trust_low = apply_tension_to_trust_decay(1.0, tension=0.0)
    trust_high = apply_tension_to_trust_decay(1.0, tension=0.95)
    
    assert trust_high < trust_low, "Trust should decay more at high tension"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
