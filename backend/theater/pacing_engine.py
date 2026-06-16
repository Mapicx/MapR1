from typing import List
from backend.theater.theater_models import TensionMetrics, PacingRecommendation, PacingMode

class PacingEngine:
    """Adjusts simulation speed based on dramatic tension."""
    
    def get_pacing_recommendation(
        self,
        mode: PacingMode,
        tension: TensionMetrics,
        history: List[TensionMetrics]
    ) -> PacingRecommendation:
        
        if mode == PacingMode.MANUAL:
            return PacingRecommendation(
                delay_seconds=0.0,
                should_pause=True,
                reason="Manual mode enabled"
            )
            
        if mode == PacingMode.AUTO_UNIFORM:
            return PacingRecommendation(
                delay_seconds=2.0,
                should_pause=False,
                reason="Uniform auto-pacing"
            )
            
        # Dramatic pacing
        current_score = tension.overall_tension
        
        # Phase transitions might warrant a pause
        if history and history[-1].phase != tension.phase:
            if tension.phase in ["climax", "resolution"]:
                return PacingRecommendation(
                    delay_seconds=0.0,
                    should_pause=True,
                    reason=f"Phase transition to {tension.phase.value}"
                )
        
        # High tension / climax
        if tension.is_climax_candidate or current_score > 0.8:
            return PacingRecommendation(
                delay_seconds=0.0,
                should_pause=True,
                reason="Climax detected - pausing for user input"
            )
            
        if current_score >= 0.5:
            return PacingRecommendation(
                delay_seconds=4.0,
                should_pause=False,
                reason="High tension - slowing down for dramatic effect"
            )
            
        if current_score >= 0.2:
            return PacingRecommendation(
                delay_seconds=2.0,
                should_pause=False,
                reason="Rising tension - standard pacing"
            )
            
        # Lull
        return PacingRecommendation(
            delay_seconds=0.5,
            should_pause=False,
            reason="Low tension lull - fast forwarding"
        )

# Global instance
pacing_engine = PacingEngine()
