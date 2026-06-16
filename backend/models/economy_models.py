"""Economy and Scarcity Models"""
from datetime import datetime
from enum import Enum
from typing import Dict, List
from uuid import uuid4, UUID
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from backend.models.db_models import Base


class ResourceType(str, Enum):
    RESOURCE_1 = "resource_1"            # Generic primary resource
    RESOURCE_2 = "resource_2"              # Generic secondary resource
    CAPITAL = "capital"            # Money, investment pools
    TALENT = "talent"              # Skilled researchers (cannot scale easily)
    TRUST = "trust"                # Public trust -- grows with transparency, shrinks with accidents
    ENFORCEMENT = "enforcement"    # Political / regulatory power
    POLITICAL_SUPPORT = "political_support"
    RESOURCE_3 = "resource_3"    # Generic tertiary resource
    WATER = "water"                # Water for cooling / data-center operations
    LITHIUM = "lithium"            # Battery / EV / infrastructure material
    PUBLIC_ATTENTION = "public_attention"  # Finite mindshare -- who gets heard


class GlobalEconomyState(Base):
    """Mutable global economy state (one row per world/project)"""
    __tablename__ = "global_economy_states"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Core macro indicators (updated each step)
    resource_1_supply = Column(Float, default=100000.0)      # Arbitrary units
    resource_2_supply = Column(Float, default=50000.0)        # Arbitrary units
    resource_3_supply = Column(Float, default=7000.0)           # Arbitrary units
    public_unemployment = Column(Float, default=0.12)     # Fraction 0-1
    gdp_growth = Column(Float, default=0.03)              # Annualized fraction
    market_confidence = Column(Float, default=0.65)       # 0-1 sentiment
    displaced_units = Column(Integer, default=0)         # Aggregate disruption

    # Per-agent / per-entity resource holdings (JSONB: {agent_id: {resource: amount}})
    agent_holdings = Column(JSONB, default=dict)

    # Market state: sector -> health (0-1)
    market_conditions = Column(JSONB, default=dict)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class PydanticGlobalEconomyState(BaseModel):
    """In-memory Pydantic version for API and simulation logic"""
    project_id: UUID
    resource_1_supply: float = 100000.0
    resource_2_supply: float = 50000.0
    resource_3_supply: float = 7000.0
    public_unemployment: float = 0.12
    gdp_growth: float = 0.03
    market_confidence: float = 0.65
    displaced_units: int = 0
    agent_holdings: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    market_conditions: Dict[str, float] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ResourceEvent(BaseModel):
    """A resource market event: price spike, supply shock, etc."""
    step: int
    resource_type: str
    change_amount: float         # positive = supply increase, negative = shortage
    price_impact: float          # multiplier to resource cost this step
    cause: str
    affected_agent_ids: List[str] = Field(default_factory=list)
