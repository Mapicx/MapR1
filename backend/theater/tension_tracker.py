from typing import List, Dict, Any, Optional
from loguru import logger
import math

from backend.models.action_models import ActionResponse, ActionType
from backend.models.world_models import StructuredWorldState
from backend.theater.theater_models import TensionMetrics, TensionPhase

class TensionTracker:
    """
    Computes dramatic tension scores based on simulation step data.
    This is a pure logic engine (no LLM calls).
    """
    
    def __init__(self):
        # Weights for tension components
        self.w_conflict = 0.35
        self.w_stakes = 0.25
        self.w_uncertainty = 0.15
        self.w_momentum = 0.15
        self.w_relationship = 0.10
        
        # Action hostility mapping
        self.hostility_map = {
            ActionType.ATTACK: 1.0,
            ActionType.SABOTAGE: 1.0,
            ActionType.BETRAY: 1.0,
            ActionType.SEEK_REVENGE: 0.9,
            ActionType.DECLARE_WAR: 1.0,
            ActionType.IMPOSE_SANCTIONS: 0.8,
            ActionType.NEGOTIATE: 0.2,
            ActionType.FORM_ALLIANCE: 0.1,
            ActionType.BUILD_RELATIONSHIP: 0.1,
            ActionType.HELP_OTHERS: 0.0,
            ActionType.TRADE: 0.2,
            ActionType.EXPAND_BUSINESS: 0.4,
            ActionType.LAUNCH_PRODUCT: 0.3,
            ActionType.ACQUIRE_COMPANY: 0.6,
            ActionType.PROPOSE_POLICY: 0.4,
            ActionType.SPREAD_IDEOLOGY: 0.5,
            ActionType.ORGANIZE_MOVEMENT: 0.6,
            ActionType.FORTIFY: 0.5,
            ActionType.BUILD_DEFENSES: 0.4,
            ActionType.GATHER_INTEL: 0.1,
            ActionType.RESEARCH: 0.1,
            ActionType.INNOVATE: 0.2,
            ActionType.WAIT: 0.0
        }

    def compute_tension(
        self,
        step: int,
        actions: List[ActionResponse],
        world_state: StructuredWorldState,
        history: List[TensionMetrics]
    ) -> TensionMetrics:
        """
        Compute the tension for the current step.
        """
        logger.debug(f"Computing tension for step {step} with {len(actions)} actions")
        
        conflict_intensity = self._calc_conflict_intensity(actions)
        stakes_level = self._calc_stakes_level(actions, world_state)
        uncertainty = self._calc_uncertainty(actions)
        momentum_shift = self._calc_momentum_shift(actions, history)
        relationship_volatility = self._calc_relationship_volatility(actions)
        
        # Calculate overall score
        overall = (
            conflict_intensity * self.w_conflict +
            stakes_level * self.w_stakes +
            uncertainty * self.w_uncertainty +
            momentum_shift * self.w_momentum +
            relationship_volatility * self.w_relationship
        )
        
        # Add explicit tension modifiers based on user rules
        tension_modifiers = 0.0
        has_hostile_success = False
        has_high_conf_fail = False
        has_betrayal = False

        for action in actions:
            if not action.success and getattr(action, 'confidence', 0.0) > 0.7:
                tension_modifiers += 0.015
                has_high_conf_fail = True
            
            if action.success:
                atype = self._map_action_to_enum(action.action_type)
                if atype in [ActionType.SABOTAGE, ActionType.ATTACK, ActionType.EXPLOIT_VULNERABILITY, ActionType.LEAK_SECRETS]:
                    tension_modifiers += 0.03
                    has_hostile_success = True

        if world_state:
            for event in world_state.recent_events:
                if event.step == step and event.action == "betrayal":
                    tension_modifiers += 0.05
                    has_betrayal = True

        overall += tension_modifiers
        overall = max(0.0, min(1.0, overall))
        
        # Add historical momentum (tension tends to carry over slightly)
        if history:
            prev_tension = history[-1].overall_tension
            # Smooth it out
            overall = (overall * 0.7) + (prev_tension * 0.3)
        
        # Determine phase and markers
        phase, is_climax, is_lull = self._determine_phase(
            overall, history, has_hostile_success, has_high_conf_fail, has_betrayal
        )
        
        # Identify sources of tension
        sources = self._identify_sources(actions)
        
        metrics = TensionMetrics(
            step=step,
            overall_tension=overall,
            conflict_intensity=conflict_intensity,
            stakes_level=stakes_level,
            uncertainty=uncertainty,
            momentum_shift=momentum_shift,
            relationship_volatility=relationship_volatility,
            is_climax_candidate=is_climax,
            is_lull=is_lull,
            phase=phase,
            tension_sources=sources
        )
        
        logger.info(f"Step {step} Tension: {overall:.2f} | Phase: {phase.value}")
        return metrics

    def _map_action_to_enum(self, action_str: str):
        action_str = str(action_str).lower().replace('_', ' ')
        
        # 1. Exact match attempt
        try:
            return ActionType(action_str.replace(' ', '_'))
        except ValueError:
            pass
            
        # 2. Fuzzy keyword matching
        best_enum = None
        max_overlap = 0
        action_words = set(action_str.split())
        
        for enum_key in self.hostility_map.keys():
            enum_words = set(enum_key.value.replace('_', ' ').split())
            overlap = len(action_words.intersection(enum_words))
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_enum = enum_key
                
        return best_enum

    def _calc_conflict_intensity(self, actions: List[ActionResponse]) -> float:
        if not actions:
            return 0.0
            
        total_hostility = 0.0
        for a in actions:
            action_enum = self._map_action_to_enum(a.action_type)
            if action_enum:
                total_hostility += self.hostility_map.get(action_enum, 0.5)
            else:
                total_hostility += 0.5
                
        return min(1.0, total_hostility / max(1, len(actions) * 0.5))

    def _calc_stakes_level(self, actions: List[ActionResponse], world_state: StructuredWorldState) -> float:
        # High stakes = actions that impact world variables or target many agents
        stakes = 0.0
        for action in actions:
            impact = action.impact or {}
            # If it changes world state markets/opinion
            if "market_conditions" in impact or "public_opinion" in impact:
                stakes += 0.5
            # If it has side effects
            if impact.get("side_effects"):
                stakes += 0.2 * len(impact["side_effects"])
                
        return min(1.0, stakes / max(1, len(actions)))

    def _calc_uncertainty(self, actions: List[ActionResponse]) -> float:
        if not actions:
            return 0.0
        # High uncertainty = actions with low confidence or failed actions
        avg_confidence = sum(a.confidence for a in actions) / len(actions)
        failure_rate = sum(1 for a in actions if a.success is False) / len(actions)
        
        uncertainty = (1.0 - avg_confidence) * 0.6 + failure_rate * 0.4
        return min(1.0, uncertainty * 1.5)

    def _calc_momentum_shift(self, actions: List[ActionResponse], history: List[TensionMetrics]) -> float:
        if not history:
            return 0.5
        
        # Look for sudden burst of successful high-impact actions
        successful_major = sum(1 for a in actions if a.success and len(a.impact.get("side_effects", [])) > 0)
        return min(1.0, successful_major * 0.3)

    def _calc_relationship_volatility(self, actions: List[ActionResponse]) -> float:
        volatility = 0.0
        for action in actions:
            atype = self._map_action_to_enum(action.action_type)
            if atype in [ActionType.BETRAY, ActionType.FORM_ALLIANCE, ActionType.DECLARE_WAR]:
                volatility += 0.5
        return min(1.0, volatility)

    def _determine_phase(
        self, current_tension: float, history: List[TensionMetrics], 
        has_hostile_success: bool = False, has_high_conf_fail: bool = False, has_betrayal: bool = False
    ) -> tuple[TensionPhase, bool, bool]:
        if not history:
            return TensionPhase.RISING_ACTION, False, current_tension < 0.2
            
        recent_tension = [h.overall_tension for h in history[-3:]]
        recent_tension.append(current_tension)
        
        avg_recent = sum(recent_tension) / len(recent_tension)
        
        is_climax = current_tension > 0.8 and avg_recent > 0.7
        is_lull = current_tension < 0.3 and avg_recent < 0.35
        
        if is_lull and (has_hostile_success or has_high_conf_fail or has_betrayal):
            is_lull = False
        
        if is_climax:
            phase = TensionPhase.CLIMAX
        elif is_lull:
            phase = TensionPhase.LULL
        elif has_betrayal:
            phase = TensionPhase.RISING_ACTION
        elif current_tension > history[-1].overall_tension:
            phase = TensionPhase.RISING_ACTION
        elif current_tension < history[-1].overall_tension - 0.1:
            phase = TensionPhase.FALLING_ACTION
        else:
            phase = TensionPhase.RESOLUTION if avg_recent < 0.5 else TensionPhase.RISING_ACTION
            
        return phase, is_climax, is_lull

    def _identify_sources(self, actions: List[ActionResponse]) -> List[str]:
        sources = []
        for action in actions:
            atype = self._map_action_to_enum(action.action_type)
            if not atype:
                continue
                
            if self.hostility_map.get(atype, 0) >= 0.8:
                sources.append(f"{action.agent_name}'s aggressive {atype.value}")
            elif not action.success:
                sources.append(f"{action.agent_name}'s failed {atype.value}")
        return sources[:3]  # Return top 3 sources

# Global instance
tension_tracker = TensionTracker()
