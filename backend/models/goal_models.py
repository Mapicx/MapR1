"""
Goal models for agent motivations and objectives.

Goals drive agent behavior and decision-making.
"""

from datetime import datetime
from uuid import UUID
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from backend.models.db_models import Base


class Goal(Base):
    """
    Agent goal/motivation.
    
    Goals can be hierarchical (parent-child relationships for sub-goals).
    """
    __tablename__ = "goals"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    parent_goal_id = Column(PGUUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=True)
    
    # Goal definition
    description = Column(Text, nullable=False)
    goal_type = Column(String(50), nullable=False)
    priority = Column(Float, nullable=False, default=0.5)  # 0-1
    
    # Progress tracking
    progress = Column(Float, nullable=False, default=0.0)  # 0-1
    status = Column(String(50), nullable=False, default="active")  # active, completed, abandoned, blocked

    # Knowledge sufficiency: how much information has been gathered toward this goal (0-1)
    # Once >= 0.65, gather_information is blocked and execution actions are preferred
    knowledge_score = Column(Float, nullable=False, default=0.0)
    
    # Timeline
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="goals")
    sub_goals = relationship("Goal", backref="parent_goal", remote_side=[id])


# ============================================================================
# Pydantic Models for API
# ============================================================================

class GoalType(str, Enum):
    """Types of goals agents can have"""
    
    # Basic needs
    SURVIVAL = "survival"
    SECURITY = "security"
    
    # Power & influence
    POWER = "power"
    INFLUENCE = "influence"
    DOMINANCE = "dominance"
    
    # Resources
    WEALTH = "wealth"
    RESOURCES = "resources"
    
    # Knowledge & growth
    KNOWLEDGE = "knowledge"
    INNOVATION = "innovation"
    SKILL = "skill"
    
    # Social
    RELATIONSHIPS = "relationships"
    REPUTATION = "reputation"
    REVENGE = "revenge"
    LOYALTY = "loyalty"
    
    # Ideological
    IDEOLOGY = "ideology"
    JUSTICE = "justice"
    FREEDOM = "freedom"
    CHANGE = "change"
    
    # Professional
    CAREER = "career"
    ACHIEVEMENT = "achievement"
    LEGACY = "legacy"


class GoalStatus(str, Enum):
    """Goal status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"


class GoalCreate(BaseModel):
    """Request to create a goal"""
    description: str = Field(..., min_length=1)
    goal_type: GoalType
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    deadline: Optional[datetime] = None
    parent_goal_id: Optional[UUID] = None


class GoalUpdate(BaseModel):
    """Request to update a goal"""
    description: Optional[str] = Field(None, min_length=1)
    goal_type: Optional[GoalType] = None
    priority: Optional[float] = Field(None, ge=0.0, le=1.0)
    status: Optional[GoalStatus] = None
    deadline: Optional[datetime] = None


class GoalProgressUpdate(BaseModel):
    """Request to update goal progress"""
    progress: float = Field(..., ge=0.0, le=1.0)


class GoalResponse(BaseModel):
    """Goal response"""
    id: UUID
    agent_id: UUID
    parent_goal_id: Optional[UUID]
    description: str
    goal_type: str
    priority: float
    progress: float
    knowledge_score: float = 0.0
    status: str
    created_at: datetime
    deadline: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class GoalContextRequest(BaseModel):
    """Request to get goal context"""
    limit: int = Field(default=5, ge=1, le=20)


# ============================================================================
# Default Goals by Agent Type
# ============================================================================

DEFAULT_GOALS_BY_TYPE = {
    "ceo": [
        {"description": "Increase company market share", "goal_type": "wealth", "priority": 0.9},
        {"description": "Build strong leadership team", "goal_type": "relationships", "priority": 0.7},
        {"description": "Maintain positive reputation", "goal_type": "reputation", "priority": 0.8},
    ],
    "hacker": [
        {"description": "Gain access to secure systems", "goal_type": "skill", "priority": 0.9},
        {"description": "Avoid detection", "goal_type": "security", "priority": 0.95},
        {"description": "Build underground network", "goal_type": "relationships", "priority": 0.6},
    ],
    "activist": [
        {"description": "Spread awareness of cause", "goal_type": "ideology", "priority": 0.95},
        {"description": "Build grassroots movement", "goal_type": "relationships", "priority": 0.8},
        {"description": "Influence policy makers", "goal_type": "influence", "priority": 0.7},
    ],
    "spy": [
        {"description": "Gather intelligence", "goal_type": "knowledge", "priority": 0.95},
        {"description": "Maintain cover identity", "goal_type": "security", "priority": 0.9},
        {"description": "Build network of informants", "goal_type": "relationships", "priority": 0.7},
    ],
    "doctor": [
        {"description": "Save lives and heal patients", "goal_type": "achievement", "priority": 0.95},
        {"description": "Advance medical knowledge", "goal_type": "knowledge", "priority": 0.7},
        {"description": "Build trusted reputation", "goal_type": "reputation", "priority": 0.8},
    ],
    "politician": [
        {"description": "Win election", "goal_type": "power", "priority": 0.9},
        {"description": "Build coalition of supporters", "goal_type": "relationships", "priority": 0.85},
        {"description": "Implement policy agenda", "goal_type": "ideology", "priority": 0.8},
    ],
}


def get_default_goals(agent_type: str) -> List[dict]:
    """Get default goals for an agent type"""
    return DEFAULT_GOALS_BY_TYPE.get(agent_type, [
        {"description": "Survive and thrive", "goal_type": "survival", "priority": 0.8},
        {"description": "Build meaningful relationships", "goal_type": "relationships", "priority": 0.6},
    ])
