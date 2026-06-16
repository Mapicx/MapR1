"""
MapR1 — Mechanical Tension Feedback System

Tension is a systemic force that intensifies consequences and accelerates instability.

As tension rises:
- Consequences become more severe
- Alliances decay faster
- Paranoia and fear increase faster
- Misinformation spreads more effectively
- Catastrophic failures become more likely

Tension thresholds define qualitative phases that trigger mechanized changes.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field

from loguru import logger


# ============================================================================
# Tension Thresholds (Mechanical Phases)
# ============================================================================

TENSION_THRESHOLDS = [
    (0.0, "stable", "Normal operations"),
    (0.2, "uneasy", "Minor tensions emerging"),
    (0.4, "unstable", "Social cohesion weakening"),
    (0.6, "volatile", "Retaliation and panic escalate"),
    (0.8, "crisis", "Catastrophic failures common"),
    (0.95, "collapse", "System failure imminent"),
]


# ============================================================================
# Tension Modifier Data Class
# ============================================================================

@dataclass
class TensionModifiers:
    """
    Complete set of tension-driven multipliers for mechanical effects.

    All multipliers are >= 1.0 (tension only intensifies effects, never dampens).
    At low tension (0.0), all modifiers are at baseline (1.0).
    """
    # Consequence severity (how hard secondary effects hit)
    consequence_severity: float

    # Action volatility (chaos in action resolution)
    action_volatility: float

    # Alliance decay rate
    alliance_decay: float

    # Paranoia amplification for psychology shifts
    paranoia_amplification: float

    # Public panic amplification for opinion shifts
    panic_amplification: float

    # Misinformation spread effectiveness
    misinformation_amplification: float

    # Betrayal probability increase
    betrayal_probability: float

    # Escalation pressure (retaliation chains)
    escalation_pressure: float

    # Instability multiplier (general system volatility)
    instability: float

    # Catastrophic outcome probability boost
    catastrophic_probability: float

    def __post_init__(self):
        # Validate all modifiers are >= 1.0
        for field in vars(self):
            value = getattr(self, field)
            if value < 1.0:
                setattr(self, field, 1.0)


# ============================================================================
# Tension Modifier System
# ============================================================================

class TensionModifierSystem:
    """
    Central tension modifier layer.

    Computes tension-driven multipliers that other systems consume to make
    tension mechanically impactful rather than cosmetic.

    The key insight: tension values scale NONLINEARLY because crisis
    tends to cascade. Each threshold crossed intensifies effects more
    dramatically than the last.
    """

    @staticmethod
    def get_modifiers(tension: float) -> TensionModifiers:
        """
        Compute tension modifiers based on current tension level.

        Uses nonlinear scaling: each threshold crossed intensifies effects
        more dramatically than the last, producing cascade behavior.

        Args:
            tension: Current tension value (0.0 to 1.0)

        Returns:
            TensionModifiers with all computed multipliers
        """
        # Normalize tension
        t = max(0.0, min(1.0, tension))

        # Nonlinear scaling function: exponential growth with tension
        # At low tension (0.0-0.2): gentle curve
        # At mid tension (0.2-0.6): moderate curve
        # At high tension (0.6+): steep curve (cascade)
        def tension_curve(tension_val: float, steepness: float = 2.5) -> float:
            """Exponential curve that accelerates effects as tension rises."""
            return 1.0 + (tension_val ** steepness) * steepness

        # Each modifier uses tension_curve with different characteristics
        # Higher modifiers = more dramatic effects

        consequence_severity = tension_curve(t, 2.0)
        action_volatility = tension_curve(t, 1.8)
        alliance_decay = tension_curve(t, 1.5)
        paranoia_amplification = tension_curve(t, 1.7)
        panic_amplification = tension_curve(t, 2.2)
        misinformation_amplification = tension_curve(t, 2.0)
        betrayal_probability = tension_curve(t, 1.9)
        escalation_pressure = tension_curve(t, 2.1)
        instability = tension_curve(t, 2.3)
        catastrophic_probability = tension_curve(t, 2.8)

        return TensionModifiers(
            consequence_severity=consequence_severity,
            action_volatility=action_volatility,
            alliance_decay=alliance_decay,
            paranoia_amplification=paranoia_amplification,
            panic_amplification=panic_amplification,
            misinformation_amplification=misinformation_amplification,
            betrayal_probability=betrayal_probability,
            escalation_pressure=escalation_pressure,
            instability=instability,
            catastrophic_probability=catastrophic_probability,
        )

    @staticmethod
    def get_phase(tension: float) -> Tuple[str, str]:
        """
        Get the tension phase name and description.

        Args:
            tension: Current tension value (0.0 to 1.0)

        Returns:
            Tuple of (phase_name, phase_description)
        """
        t = max(0.0, min(1.0, tension))

        for threshold, phase, description in reversed(TENSION_THRESHOLDS):
            if t >= threshold:
                return phase, description

        return "stable", "Normal operations"

    @staticmethod
    def get_threshold_effects(phase: str) -> Dict[str, Any]:
        """
        Get specific mechanical effects that trigger when entering a phase.

        These are discrete changes that happen AT threshold boundaries,
        not gradual modifiers.

        Args:
            phase: The tension phase name

        Returns:
            Dict of threshold-triggered effects
        """
        effects = {
            "stable": {},
            "uneasy": {
                "trust_decay_bonus": 0.05,  # Trust erodes slightly faster
            },
            "unstable": {
                "trust_decay_bonus": 0.15,
                "alliance_reliability_penalty": 0.2,  # Alliances 20% less reliable
                "catastrophic_base_increase": 0.05,  # +5% base catastrophic chance
            },
            "volatile": {
                "trust_decay_bonus": 0.3,
                "alliance_reliability_penalty": 0.4,
                "catastrophic_base_increase": 0.15,
                "psychology_acceleration": 2.0,  # Psychology shifts 2x faster
                "betrayal_threshold_bonus": 0.1,  # +10% betrayal chance
            },
            "crisis": {
                "trust_decay_bonus": 0.5,
                "alliance_reliability_penalty": 0.6,
                "catastrophic_base_increase": 0.3,
                "psychology_acceleration": 3.0,
                "betrayal_threshold_bonus": 0.25,
                "public_polarization_acceleration": 2.0,
            },
            "collapse": {
                "trust_decay_bonus": 0.8,
                "alliance_reliability_penalty": 0.8,
                "catastrophic_base_increase": 0.5,
                "psychology_acceleration": 5.0,
                "betrayal_threshold_bonus": 0.5,
                "public_polarization_acceleration": 3.0,
                "alliance_dissolution_chance": 0.3,  # 30% chance alliances dissolve
            },
        }
        return effects.get(phase, {})

    @staticmethod
    def apply_to_consequence_weights(
        weighted_outcomes: List[Tuple[Any, float]],
        tension: float,
    ) -> List[Tuple[Any, float]]:
        """
        Apply tension modifiers to consequence outcome weights.

        At high tension:
        - Catastrophic outcomes become more likely
        - Escalation-triggering outcomes amplified
        - Panic/spread outcomes amplified

        Args:
            weighted_outcomes: List of (outcome, pre_computed_weight) tuples
            tension: Current tension level

        Returns:
            List of (outcome, modified_weight) tuples
        """
        modifiers = TensionModifierSystem.get_modifiers(tension)
        weighted: List[Tuple[Any, float]] = []

        catastrophic_keys = {
            "exposed_operative", "retaliation_escalation", "public_backlash",
            "loyalty_collapse", "public_panic", "civilian_panic",
            "retaliation_planning", "market_panic", "public_scandal",
            "catastrophic_failure", "collapse"
        }

        escalation_keys = {
            "retaliation_escalation", "retaliation_planning", "escalation_spiral",
            "alliance_retaliation_triggered", "opposition_mobilization"
        }

        panic_keys = {
            "public_panic", "public_backlash", "public_fear_increase",
            "civilian_panic", "activist_mobilization"
        }

        for outcome, base_weight in weighted_outcomes:
            weight = base_weight

            # Then apply tension modifiers
            # Catastrophic outcomes become dramatically more likely at high tension
            if outcome.key in catastrophic_keys:
                weight *= modifiers.catastrophic_probability

            # Escalation outcomes intensify in volatile/crisis phases
            if outcome.key in escalation_keys:
                weight *= modifiers.escalation_pressure

            # Panic outcomes spread faster
            if outcome.key in panic_keys:
                weight *= modifiers.panic_amplification

            # General consequence severity multiplier
            weight *= modifiers.consequence_severity

            weighted.append((outcome, weight))

        return weighted

    @staticmethod
    def compute_alliance_reliability(
        base_strength: float,
        tension: float,
        trust_level: float,
    ) -> float:
        """
        Compute alliance reliability adjusted for tension.

        At high tension, even strong alliances become unreliable.

        Args:
            base_strength: The nominal alliance strength (0.0 to 1.0)
            tension: Current tension level
            trust_level: Current trust between parties

        Returns:
            Adjusted reliability factor (clamped to 0.01 minimum)
        """
        modifiers = TensionModifierSystem.get_modifiers(tension)
        phase, _ = TensionModifierSystem.get_phase(tension)
        threshold_effects = TensionModifierSystem.get_threshold_effects(phase)

        # Reliability multiplies base strength by trust and tension modifiers
        reliability = base_strength * trust_level / modifiers.alliance_decay

        return max(0.01, reliability)

    @staticmethod
    def compute_betrayal_probability(
        base_probability: float,
        tension: float,
        relationship_strength: float,
    ) -> float:
        """
        Compute adjusted betrayal probability.

        At high tension, even trusted allies may betray.

        Args:
            base_probability: Base betrayal chance
            tension: Current tension level
            relationship_strength: Current relationship strength (-1.0 to 1.0)

        Returns:
            Adjusted betrayal probability (0.0 to 1.0)
        """
        modifiers = TensionModifierSystem.get_modifiers(tension)
        phase, _ = TensionModifierSystem.get_phase(tension)
        threshold_effects = TensionModifierSystem.get_threshold_effects(phase)

        # Tension increases betrayal chance, especially for allies
        betrayal_bonus = threshold_effects.get("betrayal_threshold_bonus", 0)

        adjusted = base_probability * modifiers.betrayal_probability + betrayal_bonus

        # Allies are more likely to betray under high tension
        if relationship_strength > 0.3:
            adjusted *= modifiers.betrayal_probability * 0.5

        return min(1.0, adjusted)

    @staticmethod
    def compute_misinformation_effectiveness(
        base_effectiveness: float,
        tension: float,
    ) -> float:
        """
        Compute misinformation spread effectiveness.

        High tension makes people more susceptible to fear-based narratives.

        Args:
            base_effectiveness: Base belief shift power
            tension: Current tension level

        Returns:
            Adjusted effectiveness (0.0 to 1.0)
        """
        modifiers = TensionModifierSystem.get_modifiers(tension)

        return min(1.0, base_effectiveness * modifiers.misinformation_amplification)


# Global instance
tension_modifier_system = TensionModifierSystem()


# ============================================================================
# Integration Helpers
# ============================================================================

def apply_tension_to_psychology_delta(
    delta: float,
    tension: float,
    trait: str = "paranoia",
    tension_sensitivity: float = 1.0,
) -> float:
    """
    Apply tension multiplier to psychology state changes.

    Args:
        delta: Original psychology change amount
        tension: Current tension level
        trait: Psychology trait name
        tension_sensitivity: How sensitive this trait is to tension (1.0 = normal)

    Returns:
        Adjusted delta (amplified by tension)
    """
    modifiers = TensionModifierSystem.get_modifiers(tension)

    # Use paranoia amplification as base, but can be customized
    sensitivity_map = {
        "fear": modifiers.paranoia_amplification,
        "paranoia": modifiers.paranoia_amplification,
        "desperation": modifiers.instability,
        "radicalization": modifiers.catastrophic_probability,
    }

    base_multiplier = sensitivity_map.get(trait, modifiers.paranoia_amplification)
    return delta * base_multiplier * tension_sensitivity


def apply_tension_to_trust_decay(
    trust: float,
    tension: float,
) -> float:
    """
    Compute accelerated trust decay under high tension.

    Args:
        trust: Current trust level
        tension: Current tension level

    Returns:
        Reduced trust after tension-accelerated decay
    """
    modifiers = TensionModifierSystem.get_modifiers(tension)
    phase, _ = TensionModifierSystem.get_phase(tension)
    threshold_effects = TensionModifierSystem.get_threshold_effects(phase)

    # Decay rate increases with tension
    decay_rate = 0.02 * modifiers.alliance_decay
    bonus = threshold_effects.get("trust_decay_bonus", 0)

    new_trust = trust - decay_rate - bonus

    return max(0.0, min(1.0, new_trust))