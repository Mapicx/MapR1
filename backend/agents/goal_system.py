"""
Goal System Manager

Manages agent goals, priorities, and progress tracking.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.goal_models import Goal, GoalStatus


class GoalManager:
    """Manages agent goals and priorities"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
    
    async def add_goal(
        self,
        db: AsyncSession,
        description: str,
        goal_type: str,
        priority: float,
        deadline: Optional[datetime] = None,
        parent_goal_id: Optional[UUID] = None,
    ) -> Goal:
        """
        Add a new goal for the agent.
        
        Args:
            description: What the agent wants to achieve
            goal_type: Type of goal (survival, wealth, power, etc.)
            priority: 0-1 (how important)
            deadline: Optional deadline
            parent_goal_id: Optional parent goal (for sub-goals)
        
        Returns:
            Created Goal
        """
        logger.info(f"Agent {self.agent_id} adding goal: {description}")
        
        goal = Goal(
            id=uuid4(),
            agent_id=self.agent_id,
            parent_goal_id=parent_goal_id,
            description=description,
            goal_type=goal_type,
            priority=priority,
            progress=0.0,
            status=GoalStatus.ACTIVE.value,
            created_at=datetime.utcnow(),
            deadline=deadline,
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        
        logger.debug(f"Goal created: {goal.id}")
        return goal
    
    async def get_goal(self, db: AsyncSession, goal_id: UUID) -> Optional[Goal]:
        """Get goal by ID"""
        result = await db.execute(
            select(Goal).where(Goal.id == goal_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_goals(
        self,
        db: AsyncSession,
        limit: Optional[int] = None,
    ) -> List[Goal]:
        """
        Get all active goals, sorted by priority.
        
        Args:
            limit: Optional limit on number of goals
        
        Returns:
            List of active goals
        """
        query = select(Goal).where(
            Goal.agent_id == self.agent_id,
            Goal.status == GoalStatus.ACTIVE.value
        ).order_by(Goal.priority.desc())
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        goals = list(result.scalars().all())
        
        logger.debug(f"Agent {self.agent_id} has {len(goals)} active goals")
        return goals
    
    async def get_all_goals(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
    ) -> List[Goal]:
        """Get all goals for the agent"""
        query = select(Goal).where(Goal.agent_id == self.agent_id)
        
        if status:
            query = query.where(Goal.status == status)
        
        query = query.order_by(Goal.priority.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def update_goal(
        self,
        db: AsyncSession,
        goal_id: UUID,
        description: Optional[str] = None,
        goal_type: Optional[str] = None,
        priority: Optional[float] = None,
        status: Optional[str] = None,
        deadline: Optional[datetime] = None,
    ) -> Optional[Goal]:
        """Update goal"""
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return None
        
        if description is not None:
            goal.description = description
        if goal_type is not None:
            goal.goal_type = goal_type
        if priority is not None:
            goal.priority = priority
        if status is not None:
            goal.status = status
            if status == GoalStatus.COMPLETED.value:
                goal.completed_at = datetime.utcnow()
        if deadline is not None:
            goal.deadline = deadline
        
        await db.commit()
        await db.refresh(goal)
        
        logger.debug(f"Goal updated: {goal_id}")
        return goal
    
    async def update_progress(
        self,
        db: AsyncSession,
        goal_id: UUID,
        progress: float,
    ) -> Optional[Goal]:
        """
        Update goal progress.
        
        Automatically marks goal as completed if progress reaches 1.0.
        
        Args:
            goal_id: Goal to update
            progress: New progress (0-1)
        
        Returns:
            Updated Goal
        """
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return None
        
        # Clamp progress to 0-1
        goal.progress = min(1.0, max(0.0, progress))
        
        # Mark as completed if progress = 1.0
        if goal.progress >= 1.0 and goal.status == GoalStatus.ACTIVE.value:
            goal.status = GoalStatus.COMPLETED.value
            goal.completed_at = datetime.utcnow()
            logger.info(f"Goal completed: {goal.description}")
        
        await db.commit()
        await db.refresh(goal)
        
        return goal
    
    async def delete_goal(self, db: AsyncSession, goal_id: UUID) -> bool:
        """Delete goal"""
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return False
        
        await db.delete(goal)
        await db.commit()
        
        logger.info(f"Goal deleted: {goal_id}")
        return True
    
    async def reprioritize(
        self,
        db: AsyncSession,
        situation: str,
    ) -> List[Goal]:
        """
        Adjust goal priorities based on current situation.
        
        This is a simple heuristic-based approach.
        In Phase 3.3, we'll use LLM for intelligent reprioritization.
        
        Args:
            situation: Description of current situation
        
        Returns:
            Updated goals
        """
        logger.info(f"Reprioritizing goals based on: {situation[:50]}...")
        
        goals = await self.get_active_goals(db)
        situation_lower = situation.lower()
        
        for goal in goals:
            old_priority = goal.priority
            
            # Survival goals increase in danger
            if goal.goal_type == "survival":
                if any(word in situation_lower for word in ["danger", "threat", "attack", "crisis"]):
                    goal.priority = min(1.0, goal.priority + 0.2)
            
            # Security goals increase when threatened
            elif goal.goal_type == "security":
                if any(word in situation_lower for word in ["threat", "attack", "vulnerable"]):
                    goal.priority = min(1.0, goal.priority + 0.15)
            
            # Wealth goals decrease in crisis
            elif goal.goal_type == "wealth":
                if any(word in situation_lower for word in ["crisis", "emergency", "disaster"]):
                    goal.priority = max(0.0, goal.priority - 0.1)
            
            # Power goals increase when opportunity arises
            elif goal.goal_type == "power":
                if any(word in situation_lower for word in ["opportunity", "weakness", "vacuum"]):
                    goal.priority = min(1.0, goal.priority + 0.1)
            
            # Revenge goals increase when wronged
            elif goal.goal_type == "revenge":
                if any(word in situation_lower for word in ["betrayed", "wronged", "attacked"]):
                    goal.priority = min(1.0, goal.priority + 0.3)
            
            if goal.priority != old_priority:
                logger.debug(f"Goal priority changed: {goal.description} ({old_priority:.2f} → {goal.priority:.2f})")
        
        await db.commit()
        return goals
    
    async def update_knowledge_score(
        self,
        db: AsyncSession,
        goal_id: UUID,
        gain: float,
    ) -> Optional[Goal]:
        """
        Increase the knowledge_score for a goal by `gain`.
        Clamped to [0.0, 1.0].
        """
        goal = await self.get_goal(db, goal_id)
        if not goal:
            return None
        goal.knowledge_score = min(1.0, max(0.0, (goal.knowledge_score or 0.0) + gain))
        await db.commit()
        await db.refresh(goal)
        logger.info(
            f"Goal '{goal.description[:40]}' knowledge_score -> {goal.knowledge_score:.2f}"
        )
        return goal

    async def get_knowledge_scores(self, db: AsyncSession) -> Dict[UUID, float]:
        """Return {goal_id: knowledge_score} for all active goals."""
        goals = await self.get_active_goals(db)
        return {g.id: (g.knowledge_score or 0.0) for g in goals}

    async def get_goal_context(
        self,
        db: AsyncSession,
        limit: int = 5,
    ) -> str:
        """
        Build context string of current goals for LLM.
        Includes knowledge_score so the agent knows when it has enough info.
        """
        goals = await self.get_active_goals(db, limit=limit)

        if not goals:
            return "No active goals."

        context_parts = ["=== CURRENT GOALS ==="]
        for i, goal in enumerate(goals, 1):
            progress_emoji = "🎯" if goal.progress < 0.3 else "⏳" if goal.progress < 0.7 else "✅"
            ks = goal.knowledge_score or 0.0
            knowledge_label = (
                "READY TO ACT" if ks >= 0.65
                else f"gathering intel ({ks:.0%} known)"
            )
            context_parts.append(
                f"{i}. {progress_emoji} {goal.description} "
                f"(priority: {goal.priority:.1f}, progress: {goal.progress:.0%}, "
                f"knowledge: {knowledge_label})"
            )

        return "\n".join(context_parts)
    
    async def get_goal_stats(self, db: AsyncSession) -> dict:
        """Get statistics about agent's goals"""
        all_goals = await self.get_all_goals(db)
        
        if not all_goals:
            return {
                "total": 0,
                "active": 0,
                "completed": 0,
                "abandoned": 0,
                "blocked": 0,
                "avg_priority": 0.0,
                "avg_progress": 0.0,
            }
        
        # Count by status
        by_status = {}
        for goal in all_goals:
            by_status[goal.status] = by_status.get(goal.status, 0) + 1
        
        # Calculate averages for active goals
        active_goals = [g for g in all_goals if g.status == GoalStatus.ACTIVE.value]
        avg_priority = sum(g.priority for g in active_goals) / len(active_goals) if active_goals else 0.0
        avg_progress = sum(g.progress for g in active_goals) / len(active_goals) if active_goals else 0.0
        
        return {
            "total": len(all_goals),
            "active": by_status.get(GoalStatus.ACTIVE.value, 0),
            "completed": by_status.get(GoalStatus.COMPLETED.value, 0),
            "abandoned": by_status.get(GoalStatus.ABANDONED.value, 0),
            "blocked": by_status.get(GoalStatus.BLOCKED.value, 0),
            "avg_priority": round(avg_priority, 2),
            "avg_progress": round(avg_progress, 2),
        }
