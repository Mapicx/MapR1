"""Public Belief, Trust, and Misinformation Graph"""
from datetime import datetime
from typing import Dict
from uuid import uuid4, UUID
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from backend.models.db_models import Base

class FactRecord(BaseModel):
    """Rich metadata for a known fact."""
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = "unknown"
    step_learned: int = 0

class PublicBeliefState(Base):
    """Tracks beliefs of the general public."""
    __tablename__ = "public_belief_states"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    # topic -> confidence in what public believes (0.0 to 1.0)
    beliefs = Column(JSONB, default=dict)
    
    # source_name -> trust score (0.0 to 1.0)
    source_to_trust = Column(JSONB, default=dict)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentBeliefState(Base):
    """What each specific agent believes."""
    __tablename__ = "agent_belief_states"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, unique=True)

    # topic -> dict matching FactRecord schema
    known_facts = Column(JSONB, default=dict)
    
    # agent_id (str) -> trust_score (0.0 to 1.0)
    trust_in_others = Column(JSONB, default=dict)
    
    # How effective they are at spreading misinformation
    propaganda_power = Column(Float, default=0.5)
    
    # How much others believe them initially
    credibility = Column(Float, default=0.5)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic APIs
class PydanticPublicBeliefState(BaseModel):
    project_id: UUID
    beliefs: Dict[str, float] = Field(default_factory=dict)
    source_to_trust: Dict[str, float] = Field(default_factory=dict)

    class Config:
        from_attributes = True

class PydanticAgentBeliefState(BaseModel):
    agent_id: UUID
    known_facts: Dict[str, FactRecord] = Field(default_factory=dict)
    trust_in_others: Dict[str, float] = Field(default_factory=dict)
    propaganda_power: float = 0.5
    credibility: float = 0.5

    class Config:
        from_attributes = True
