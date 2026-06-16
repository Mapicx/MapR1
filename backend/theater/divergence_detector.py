from typing import List, Optional
from loguru import logger
from backend.models.action_models import ActionResponse
from backend.models.world_models import StructuredWorldState
from backend.theater.theater_models import TensionMetrics, DivergencePoint, DivergenceBranch

class DivergenceDetector:
    """Detects moments where timeline branching would be most interesting."""
    
    def detect_divergence(
        self,
        step: int,
        actions: List[ActionResponse],
        tension: TensionMetrics,
        world_state: StructuredWorldState,
    ) -> Optional[DivergencePoint]:
        
        # Divergence criteria
        # 1. Very high tension (Climax)
        if tension.is_climax_candidate:
            logger.info("Divergence detected: Climax")
            return self._create_divergence(
                step, "Climax reached in tension arc", tension.overall_tension, actions
            )
            
        # 2. Major failed action with high confidence
        for action in actions:
            if not action.success and action.confidence > 0.8:
                logger.info(f"Divergence detected: Major failure for {action.agent_name}")
                return self._create_divergence(
                    step, f"{action.agent_name}'s highly confident action failed", 0.7, actions
                )
                
        # 3. Sudden momentum shift
        if tension.momentum_shift > 0.6:
            logger.info("Divergence detected: Major momentum shift")
            return self._create_divergence(
                step, "A major shift in momentum occurred", tension.momentum_shift, actions
            )
            
        return None

    def _create_divergence(
        self,
        step: int,
        reason: str,
        significance: float,
        actions: List[ActionResponse]
    ) -> DivergencePoint:
        
        # Create some standard what-if branches
        branches = []
        
        # Look for failed actions to create a "What if it succeeded?" branch
        for action in actions:
            if action.success is False:
                branches.append(DivergenceBranch(
                    label=f"What if {action.agent_name}'s action succeeded?",
                    description=f"{action.agent_name} successfully completes: {action.description}",
                    modifications={
                        "actions": {
                            str(action.agent_id): {"success": True}
                        }
                    },
                    estimated_impact="Could shift the balance of power"
                ))
            elif action.success is True:
                branches.append(DivergenceBranch(
                    label=f"What if {action.agent_name}'s action failed?",
                    description=f"{action.agent_name} fails to: {action.description}",
                    modifications={
                        "actions": {
                            str(action.agent_id): {"success": False}
                        }
                    },
                    estimated_impact="Could expose their vulnerabilities"
                ))
                
        # Fallback branch if nothing specific
        if not branches:
            branches.append(DivergenceBranch(
                label="Inject random chaos",
                description="An unexpected external event occurs",
                modifications={"inject_wildcard": True},
                estimated_impact="Unpredictable"
            ))
            
        return DivergencePoint(
            step=step,
            description=reason,
            significance=significance,
            branches=branches[:3], # Max 3 branches
            world_state_snapshot={}, # To be filled by orchestrator
            agent_states_snapshot={} # To be filled by orchestrator
        )

# Global instance
divergence_detector = DivergenceDetector()
