"""
World state models for MapR1
Tracks the current state of a world/simulation
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4
from pydantic import BaseModel, Field

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.models.db_models import Base


class WorldState(Base):
    """
    World state snapshot - tracks the current state of a world
    This is different from Project which is just a container
    """
    
    __tablename__ = "world_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Current state as JSONB
    state = Column(JSONB, nullable=False, default=dict)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="world_state")
    events = relationship("WorldEvent", back_populates="world_state", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "state": self.state,
            "last_updated": self.last_updated.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class WorldEvent(Base):
    """
    World events - significant events that affect the world state
    Different from timeline_events which are part of scenarios
    """
    
    __tablename__ = "world_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_state_id = Column(UUID(as_uuid=True), ForeignKey("world_states.id", ondelete="CASCADE"), nullable=False)
    
    # Event data
    event_type = Column(String(100), nullable=False)  # war, treaty, discovery, disaster, etc.
    description = Column(Text, nullable=False)
    impact_score = Column(Float, nullable=True)  # -1.0 to 1.0 (negative to positive impact)
    affected_entity_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Entities affected by this event
    
    # Metadata
    occurred_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    world_state = relationship("WorldState", back_populates="events")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "world_state_id": str(self.world_state_id),
            "event_type": self.event_type,
            "description": self.description,
            "impact_score": self.impact_score,
            "affected_entity_ids": [str(eid) for eid in self.affected_entity_ids] if self.affected_entity_ids else [],
            "occurred_at": self.occurred_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# Phase 2: Structured World State Models
# ============================================================================

class AllianceRecord(BaseModel):
    """Record of an alliance between two agents"""
    agent_a: str  # agent_id
    agent_b: str  # agent_id
    formed_at_step: int
    strength: float = Field(..., ge=0.0, le=1.0, description="Alliance strength (0-1)")
    alliance_type: str = "strategic"  # "strategic", "defensive", "trade"


class RivalryRecord(BaseModel):
    """Record of a rivalry/conflict between two agents"""
    agent_a: str  # agent_id
    agent_b: str  # agent_id
    started_at_step: int
    intensity: float = Field(..., ge=0.0, le=1.0, description="Rivalry intensity (0-1)")
    cause: str  # "attack", "sabotage", "competition", etc.


class WorldEventRecord(BaseModel):
    """Record of a significant world event"""
    step: int
    actor: str  # agent name or "system"
    action: str  # what happened
    target: Optional[str] = None  # who was affected
    outcome: str  # description of what happened
    visibility: float = Field(..., ge=0.0, le=1.0, description="How public this event is (0-1)")


class StructuredWorldState(BaseModel):
    """
    Structured world state that action executors mutate consistently.
    
    This replaces the freeform state dict with structured tracking of:
    - Agent-level metrics (resources, reputation, power, exposure)
    - Relationships (alliances, rivalries)
    - Global state (public opinion, market conditions, regulatory pressure)
    - Recent events for situation building
    """
    
    # ── Agent-level state ──
    agent_resources: Dict[str, float] = Field(
        default_factory=dict,
        description="agent_id → resource level (0-1)"
    )
    agent_reputation: Dict[str, float] = Field(
        default_factory=dict,
        description="agent_id → public reputation (0-1)"
    )
    agent_power: Dict[str, float] = Field(
        default_factory=dict,
        description="agent_id → power/influence level (0-1)"
    )
    agent_exposure: Dict[str, float] = Field(
        default_factory=dict,
        description="agent_id → how exposed/visible (0-1)"
    )
    
    # ── Relationship-level state ──
    alliances: List[AllianceRecord] = Field(
        default_factory=list,
        description="Active alliances between agents"
    )
    rivalries: List[RivalryRecord] = Field(
        default_factory=list,
        description="Active rivalries/conflicts"
    )
    # Track unresponded proposals
    pending_proposals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata about the simulation
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # ── Global state ──
    tension: float = Field(
        default=0.0,
        description="Global tension level (0-1)"
    )
    public_opinion: Dict[str, float] = Field(
        default_factory=dict,
        description="topic → sentiment (-1 to 1)"
    )
    market_conditions: Dict[str, float] = Field(
        default_factory=dict,
        description="sector → health (0-1)"
    )
    regulatory_pressure: Dict[str, float] = Field(
        default_factory=dict,
        description="company/sector → pressure (0-1)"
    )
    media_attention: Dict[str, float] = Field(
        default_factory=dict,
        description="topic → attention level (0-1)"
    )
    
    # ── Event log (last N steps) ──
    recent_events: List[WorldEventRecord] = Field(
        default_factory=list,
        description="Last 10 events for situation building"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "agent_resources": self.agent_resources,
            "agent_reputation": self.agent_reputation,
            "agent_power": self.agent_power,
            "agent_exposure": self.agent_exposure,
            "alliances": [a.dict() for a in self.alliances],
            "rivalries": [r.dict() for r in self.rivalries],
            "public_opinion": self.public_opinion,
            "market_conditions": self.market_conditions,
            "regulatory_pressure": self.regulatory_pressure,
            "media_attention": self.media_attention,
            "recent_events": [e.dict() for e in self.recent_events],
            "pending_proposals": self.pending_proposals,
            "tension": self.tension,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredWorldState":
        """Create from dictionary"""
        # Convert nested dicts back to models
        alliances = [AllianceRecord(**a) for a in data.get("alliances", [])]
        rivalries = [RivalryRecord(**r) for r in data.get("rivalries", [])]
        recent_events = [WorldEventRecord(**e) for e in data.get("recent_events", [])]
        
        return cls(
            agent_resources=data.get("agent_resources", {}),
            agent_reputation=data.get("agent_reputation", {}),
            agent_power=data.get("agent_power", {}),
            agent_exposure=data.get("agent_exposure", {}),
            alliances=alliances,
            rivalries=rivalries,
            public_opinion=data.get("public_opinion", {}),
            market_conditions=data.get("market_conditions", {}),
            regulatory_pressure=data.get("regulatory_pressure", {}),
            media_attention=data.get("media_attention", {}),
            recent_events=recent_events,
            pending_proposals=data.get("pending_proposals", []),
            tension=data.get("tension", 0.0),
        )
    
    @classmethod
    def from_legacy_state(cls, legacy_state: Dict[str, Any]) -> "StructuredWorldState":
        """
        Migrate from legacy freeform state dict to structured state.
        Preserves any existing data.
        """
        # If it's already structured, just load it
        if "agent_resources" in legacy_state:
            return cls.from_dict(legacy_state)
        
        # Otherwise, create empty structured state
        # (legacy data can be preserved in a "legacy" field if needed)
        return cls()
