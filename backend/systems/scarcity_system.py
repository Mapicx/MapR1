from typing import Tuple, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.economy_models import GlobalEconomyState
from backend.models.action_models import ActionType


class ScarcityEngine:
    """
    Evaluates resource scarcity to dynamically block or penalize agent actions 
    before they are executed.
    """

    def __init__(self):
        # Explicit mapping of the MINIMUM required resources to even attempt an action.
        # This is purely for the scarcity evaluation (feasibility).
        # Actual consumption happens in the EconomySystem after execution.
        self.action_requirements: Dict[str, Dict[str, float]] = {
            ActionType.EXPAND_BUSINESS.value: {"resource_1": 2000.0, "capital": 0.0},
            ActionType.LAUNCH_PRODUCT.value: {"resource_1": 1000.0, "resource_2": 500.0},
            ActionType.INNOVATE.value: {"resource_1": 5000.0, "resource_2": 2000.0},
            ActionType.RESEARCH.value: {"resource_1": 3000.0, "resource_2": 1000.0},
            ActionType.SABOTAGE.value: {"resource_1": 500.0, "resource_2": 500.0},
            ActionType.FORTIFY.value: {"resource_1": 1000.0},
            ActionType.BUILD_DEFENSES.value: {"resource_1": 1000.0, "resource_2": 500.0},
        }
        
        # At what multiple of the cost do we consider the resource "strained"?
        # E.g. if we need 2000 compute, and the global pool has < 6000, it's strained.
        self.strain_threshold_multiplier = 3.0

    async def evaluate_action(
        self, db: AsyncSession, project_id: UUID, action_type: str
    ) -> Tuple[bool, float, str]:
        """
        Evaluate if an action is affordable and determine scarcity penalties.
        
        Returns:
            is_blocked (bool): True if the action absolutely cannot be afforded.
            success_penalty (float): Probability reduction (0.0 to 1.0) if strained.
            reason (str): Explanatory text for logs and UI.
        """
        requirements = self.action_requirements.get(action_type)
        
        # If action doesn't require specific macro resources, it passes easily
        if not requirements:
            return False, 0.0, ""

        economy = await self._get_economy_state(db, project_id)
        if not economy:
            # If economy hasn't been initialized, we don't block.
            return False, 0.0, ""

        max_penalty = 0.0
        strained_resources = []

        for resource, cost in requirements.items():
            current_supply = getattr(economy, f"{resource}_supply", None)
            
            # If the model doesn't track this resource, skip
            if current_supply is None:
                continue
                
            # 1. Hard Block: Literally unaffordable
            if current_supply < cost:
                return True, 0.0, f"Global {resource} shortage ({current_supply:,.0f} available < {cost:,.0f} required)"

            # 2. Probabilistic Penalty: Action is possible but resources are strained
            strain_threshold = cost * self.strain_threshold_multiplier
            if current_supply < strain_threshold:
                # The closer we are to 0 (relative to threshold), the higher the penalty.
                # E.g., cost=2000, threshold=6000, current=3000 -> penalty proportion = (6000-3000)/(6000-2000) = 3000/4000 = 0.75
                # Max penalty per strained resource is 0.4.
                penalty_ratio = (strain_threshold - current_supply) / (strain_threshold - cost)
                penalty = 0.4 * penalty_ratio
                
                max_penalty = max(max_penalty, penalty)
                strained_resources.append(resource)

        if strained_resources:
            reason = f"Strained {', '.join(strained_resources)} resources severely penalize success probability."
            return False, max_penalty, reason

        return False, 0.0, ""

    async def _get_economy_state(self, db: AsyncSession, project_id: UUID) -> GlobalEconomyState:
        result = await db.execute(select(GlobalEconomyState).where(GlobalEconomyState.project_id == project_id))
        return result.scalar_one_or_none()
