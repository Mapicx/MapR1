"""
Relationship models for agent-to-agent connections.

Tracks relationships, trust, influence, and interaction history.
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


class AgentRelationship(Base):
    """
    Relationship between two agents.
    
    Tracks strength, trust, influence, and interaction history.
    """
    __tablename__ = "agent_relationships"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Agents involved
    agent_a_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_b_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Relationship properties
    relationship_type = Column(String(50), nullable=False, default="neutral")
    strength = Column(Float, nullable=False, default=0.0)  # -1 to 1 (hostile to friendly)
    trust = Column(Float, nullable=False, default=0.5)  # 0 to 1
    influence = Column(Float, nullable=False, default=0.0)  # -1 to 1 (A influences B)
    
    # History
    interaction_count = Column(Integer, nullable=False, default=0)
    last_interaction = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project")
    agent_a = relationship("Agent", foreign_keys=[agent_a_id], backref="relationships_as_a")
    agent_b = relationship("Agent", foreign_keys=[agent_b_id], backref="relationships_as_b")
    interactions = relationship("AgentInteraction", back_populates="relationship", cascade="all, delete-orphan")


class AgentInteraction(Base):
    """
    Record of interaction between agents.
    
    Tracks how interactions affect relationships over time.
    """
    __tablename__ = "agent_interactions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    relationship_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_relationships.id", ondelete="CASCADE"), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    outcome = Column(String(50), nullable=False)  # positive, negative, neutral
    
    # Impact on relationship
    trust_change = Column(Float, nullable=False, default=0.0)
    strength_change = Column(Float, nullable=False, default=0.0)
    
    # Metadata
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    relationship = relationship("AgentRelationship", back_populates="interactions")


# ============================================================================
# Pydantic Models for API
# ============================================================================

class RelationshipType(str, Enum):
    """Types of relationships between agents"""
    
    # Positive
    ALLY = "ally"
    FRIEND = "friend"
    MENTOR = "mentor"
    PARTNER = "partner"
    
    # Negative
    ENEMY = "enemy"
    RIVAL = "rival"
    
    # Neutral
    NEUTRAL = "neutral"
    ACQUAINTANCE = "acquaintance"
    
    # Hierarchical
    SUPERIOR = "superior"
    SUBORDINATE = "subordinate"
    
    # Economic
    TRADE_PARTNER = "trade_partner"
    COMPETITOR = "competitor"
    
    # Social
    FAMILY = "family"
    COLLEAGUE = "colleague"


class InteractionType(str, Enum):
    """Types of interactions between agents"""
    COOPERATION = "cooperation"
    CONFLICT = "conflict"
    TRADE = "trade"
    COMMUNICATION = "communication"
    NEGOTIATION = "negotiation"
    BETRAYAL = "betrayal"
    SUPPORT = "support"
    ATTACK = "attack"


class InteractionOutcome(str, Enum):
    """Outcome of an interaction"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class RelationshipCreate(BaseModel):
    """Request to create a relationship"""
    other_agent_id: UUID
    relationship_type: RelationshipType = RelationshipType.NEUTRAL
    strength: float = Field(default=0.0, ge=-1.0, le=1.0)
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    influence: float = Field(default=0.0, ge=-1.0, le=1.0)


class RelationshipUpdate(BaseModel):
    """Request to update a relationship"""
    relationship_type: Optional[RelationshipType] = None
    strength: Optional[float] = Field(None, ge=-1.0, le=1.0)
    trust: Optional[float] = Field(None, ge=0.0, le=1.0)
    influence: Optional[float] = Field(None, ge=-1.0, le=1.0)


class InteractionCreate(BaseModel):
    """Request to record an interaction"""
    interaction_type: InteractionType
    description: str = Field(..., min_length=1)
    outcome: InteractionOutcome
    trust_change: float = Field(default=0.0, ge=-1.0, le=1.0)
    strength_change: float = Field(default=0.0, ge=-1.0, le=1.0)


class RelationshipResponse(BaseModel):
    """Relationship response"""
    id: UUID
    project_id: UUID
    agent_a_id: UUID
    agent_b_id: UUID
    relationship_type: str
    strength: float
    trust: float
    influence: float
    interaction_count: int
    last_interaction: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class InteractionResponse(BaseModel):
    """Interaction response"""
    id: UUID
    relationship_id: UUID
    interaction_type: str
    description: str
    outcome: str
    trust_change: float
    strength_change: float
    occurred_at: datetime
    
    class Config:
        from_attributes = True


class RelationshipSummary(BaseModel):
    """Summary of an agent's relationships"""
    total_relationships: int
    allies: int
    enemies: int
    neutral: int
    avg_trust: float
    avg_strength: float
    total_interactions: int


class RelationshipContextRequest(BaseModel):
    """Request to get relationship context"""
    limit: int = Field(default=10, ge=1, le=50)
