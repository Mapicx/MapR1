"""
MapR1 — Action Cooldown & Repetition Prevention System

Tracks recently attempted actions per agent and applies penalties/blocks
to prevent agents from spamming the same action repeatedly.

Rules:
- Same exact action: blocked for 3 steps after attempt
- Same action category: 50% penalty for 2 steps
- Failed action: longer cooldown (5 steps) — don't repeat failures
- World state change resets cooldowns for affected action categories
"""

from typing import List, Set, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.models.action_models import AgentAction, CandidateAction, RecentAction


# ── Cooldown Configuration ──────────────────────────────────────────────────

# Cooldown durations (in simulation steps)
EXACT_ACTION_COOLDOWN = 3        # Can't repeat exact same action for 3 steps
CATEGORY_COOLDOWN = 2            # Same category has penalty for 2 steps
FAILED_ACTION_COOLDOWN = 5       # Failed actions blocked longer
CATEGORY_PENALTY_MULTIPLIER = 0.5  # Penalty applied to goal_alignment score


# Categories that map action types to groups
# This uses the action_router's handler names as categories
ACTION_CATEGORIES = {
    "gather_information": "intelligence",
    "expansion": "business",
    "product_launch": "business",
    "acquisition": "business",
    "alliance": "diplomacy",
    "attack": "aggression",
    "sabotage": "aggression",
    "campaign": "influence",
    "negotiation": "diplomacy",
    "investment": "financial",
    "policy": "governance",
    "talent": "business",
    "financial": "financial",
    "gather_intel": "passive",
    "relationship_building": "social",
    "generic": "general",
}


class ActionCooldownManager:
    """
    Tracks recently attempted actions and applies cooldown penalties.
    
    Prevents agents from spamming the same action repeatedly by:
    1. Blocking exact action repeats for N steps
    2. Penalizing same-category actions
    3. Longer blocks for failed actions
    4. Resetting cooldowns when world state changes
    """

    async def get_recent_actions(
        self, 
        db: AsyncSession, 
        agent_id: UUID, 
        lookback_steps: int = 5
    ) -> List[RecentAction]:
        """
        Query AgentAction table for this agent's recent actions.
        
        Args:
            db: Database session
            agent_id: Agent to query
            lookback_steps: How many steps back to look
            
        Returns:
            List of RecentAction objects
        """
        try:
            # Get the agent's recent actions, ordered by step descending
            result = await db.execute(
                select(AgentAction)
                .where(AgentAction.agent_id == agent_id)
                .order_by(AgentAction.simulation_step.desc())
                .limit(lookback_steps)
            )
            actions = list(result.scalars().all())
            
            recent = []
            for action in actions:
                # Map action_type to category using action_router
                category = self._get_action_category(action.action_type)
                
                recent.append(RecentAction(
                    action_type=action.action_type,
                    action_category=category,
                    step_number=action.simulation_step,
                    success=action.success if action.success is not None else True,
                    outcome=action.outcome or "unknown",
                ))
            
            logger.debug(f"Loaded {len(recent)} recent actions for agent {agent_id}")
            return recent
            
        except Exception as e:
            logger.error(f"Failed to load recent actions: {e}")
            return []

    def apply_cooldowns(
        self,
        candidates: List[CandidateAction],
        recent_actions: List[RecentAction],
        current_step: int,
    ) -> List[CandidateAction]:
        """
        Apply cooldown penalties to candidate actions.
        
        Rules:
        - Exact action match within EXACT_ACTION_COOLDOWN steps: BLOCKED (removed)
        - Failed action within FAILED_ACTION_COOLDOWN steps: BLOCKED
        - Same category within CATEGORY_COOLDOWN steps: PENALIZED (reduce goal_alignment)
        
        Args:
            candidates: List of candidate actions to filter
            recent_actions: Recent actions from database
            current_step: Current simulation step number
            
        Returns:
            Filtered and penalized list of candidates
        """
        if not recent_actions:
            return candidates
        
        filtered = []
        
        for candidate in candidates:
            # Check for exact action cooldown
            if self._is_exact_action_blocked(candidate, recent_actions, current_step):
                logger.debug(
                    f"Blocking '{candidate.display_name}' - exact action cooldown active"
                )
                continue
            
            # Check for failed action cooldown
            if self._is_failed_action_blocked(candidate, recent_actions, current_step):
                logger.debug(
                    f"Blocking '{candidate.display_name}' - failed action cooldown active"
                )
                continue
            
            # Apply category penalty if applicable
            penalty = self._calculate_category_penalty(candidate, recent_actions, current_step)
            if penalty > 0:
                # Reduce goal_alignment by penalty
                original_alignment = candidate.goal_alignment
                candidate.goal_alignment = max(0.0, candidate.goal_alignment * (1.0 - penalty))
                candidate.cooldown_penalty = penalty
                
                logger.debug(
                    f"Penalizing '{candidate.display_name}' - category cooldown "
                    f"(alignment: {original_alignment:.2f} -> {candidate.goal_alignment:.2f})"
                )
            
            filtered.append(candidate)
        
        logger.info(
            f"Cooldown filter: {len(candidates)} candidates -> {len(filtered)} after filtering"
        )
        return filtered

    def check_world_state_change(
        self,
        old_world_state: Dict,
        new_world_state: Dict,
    ) -> Set[str]:
        """
        Returns set of action categories whose cooldowns should be reset
        because the world state changed in a relevant way.
        
        For example:
        - If "market_conditions" changed -> reset "business", "financial" categories
        - If "political_climate" changed -> reset "governance", "diplomacy" categories
        
        Args:
            old_world_state: Previous world state dict
            new_world_state: Current world state dict
            
        Returns:
            Set of category names to reset cooldowns for
        """
        categories_to_reset = set()
        
        # Define which world state keys affect which action categories
        state_to_category_map = {
            "market_conditions": {"business", "financial"},
            "economy": {"business", "financial"},
            "political_climate": {"governance", "diplomacy"},
            "regulations": {"governance", "business"},
            "public_opinion": {"influence", "social"},
            "technology": {"business", "intelligence"},
            "security_level": {"aggression", "intelligence"},
        }
        
        # Check for changes in world state
        for key, affected_categories in state_to_category_map.items():
            old_value = old_world_state.get(key)
            new_value = new_world_state.get(key)
            
            if old_value != new_value:
                logger.debug(
                    f"World state change detected: {key} changed from {old_value} to {new_value}"
                )
                categories_to_reset.update(affected_categories)
        
        if categories_to_reset:
            logger.info(
                f"Resetting cooldowns for categories: {categories_to_reset} "
                f"due to world state changes"
            )
        
        return categories_to_reset

    # ── Private Helper Methods ──────────────────────────────────────────────

    def _get_action_category(self, action_type: str) -> str:
        """
        Map an action_type to its category.
        
        Uses action_router to get the handler name, then maps to category.
        Falls back to keyword matching if router not available.
        """
        # Try to use action_router for semantic mapping (lazy import to avoid circular dependency)
        try:
            from backend.simulation.action_router import action_router
            if action_router.is_ready:
                handler_name, _ = action_router.route(action_type)
                return ACTION_CATEGORIES.get(handler_name, "general")
        except ImportError:
            pass
        
        # Fallback: direct lookup or keyword matching
        action_lower = action_type.lower()
        
        # Direct lookup
        if action_lower in ACTION_CATEGORIES:
            return ACTION_CATEGORIES[action_lower]
        
        # Keyword matching
        if "gather" in action_lower or "intel" in action_lower:
            return "intelligence"
        if "expand" in action_lower or "launch" in action_lower or "product" in action_lower:
            return "business"
        if "acquire" in action_lower or "takeover" in action_lower:
            return "business"
        if "alliance" in action_lower or "partner" in action_lower:
            return "diplomacy"
        if "attack" in action_lower or "sabotage" in action_lower:
            return "aggression"
        if "campaign" in action_lower or "protest" in action_lower or "expose" in action_lower:
            return "influence"
        if "negotiate" in action_lower or "deal" in action_lower:
            return "diplomacy"
        if "invest" in action_lower or "fund" in action_lower:
            return "financial"
        if "policy" in action_lower or "regulat" in action_lower:
            return "governance"
        if "hire" in action_lower or "recruit" in action_lower or "poach" in action_lower:
            return "business"
        if "gather_intel" in action_lower or "wait" in action_lower:
            return "passive"
        if "help" in action_lower or "support" in action_lower or "relationship" in action_lower:
            return "social"
        
        return "general"

    def _is_exact_action_blocked(
        self,
        candidate: CandidateAction,
        recent_actions: List[RecentAction],
        current_step: int,
    ) -> bool:
        """Check if this exact action is in cooldown period."""
        for recent in recent_actions:
            # Check if action names match (normalize for comparison)
            if self._normalize_action_name(recent.action_type) == \
               self._normalize_action_name(candidate.action_name):
                steps_ago = current_step - recent.step_number
                if steps_ago <= EXACT_ACTION_COOLDOWN:
                    return True
        return False

    def _is_failed_action_blocked(
        self,
        candidate: CandidateAction,
        recent_actions: List[RecentAction],
        current_step: int,
    ) -> bool:
        """Check if this action failed recently and is in extended cooldown."""
        for recent in recent_actions:
            if self._normalize_action_name(recent.action_type) == \
               self._normalize_action_name(candidate.action_name):
                if not recent.success:
                    steps_ago = current_step - recent.step_number
                    if steps_ago <= FAILED_ACTION_COOLDOWN:
                        return True
        return False

    def _calculate_category_penalty(
        self,
        candidate: CandidateAction,
        recent_actions: List[RecentAction],
        current_step: int,
    ) -> float:
        """
        Calculate penalty for same-category actions.
        
        Returns penalty multiplier (0.0 = no penalty, 0.5 = 50% penalty)
        """
        candidate_category = self._get_action_category(candidate.action_name)
        
        for recent in recent_actions:
            if recent.action_category == candidate_category:
                steps_ago = current_step - recent.step_number
                if steps_ago <= CATEGORY_COOLDOWN:
                    # Penalty decreases with time
                    # Step 1 ago: 50% penalty, Step 2 ago: 25% penalty
                    time_factor = (CATEGORY_COOLDOWN - steps_ago + 1) / CATEGORY_COOLDOWN
                    return CATEGORY_PENALTY_MULTIPLIER * time_factor
        
        return 0.0

    def _normalize_action_name(self, action: str) -> str:
        """Normalize action name for comparison (lowercase, remove special chars)."""
        return action.lower().replace("_", " ").replace("-", " ").strip()
