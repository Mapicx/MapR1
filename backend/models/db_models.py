"""
MapR1 — Database Models
SQLAlchemy models for Supabase PostgreSQL.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Import models to resolve forward references
if TYPE_CHECKING:
    from backend.models.entity_models import Entity
    from backend.models.timeline_models import Timeline
    from backend.models.world_models import WorldState
    from backend.models.agent_models import Agent


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class Project(Base):
    """Project/World container for scenarios"""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships - using string references to avoid circular imports
    scenarios: Mapped[List["DBScenario"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    entities: Mapped[List["Entity"]] = relationship(
        "Entity", back_populates="project", cascade="all, delete-orphan"
    )
    timelines: Mapped[List["Timeline"]] = relationship(
        "Timeline", back_populates="project", cascade="all, delete-orphan"
    )
    world_state: Mapped[Optional["WorldState"]] = relationship(
        "WorldState", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    agents: Mapped[List["Agent"]] = relationship(
        "Agent", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


class DBScenario(Base):
    """Stored scenario with timeline events"""
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Scenario data
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    saved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="scenarios")
    timeline_events: Mapped[List["DBTimelineEvent"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", order_by="DBTimelineEvent.sequence_order"
    )
    timelines: Mapped[List["Timeline"]] = relationship(
        secondary="timeline_scenarios", back_populates="scenarios"
    )

    def __repr__(self) -> str:
        return f"<DBScenario(id={self.id}, title='{self.title}')>"


class DBTimelineEvent(Base):
    """Timeline event belonging to a scenario"""
    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    
    # Event data
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    scenario: Mapped["DBScenario"] = relationship(back_populates="timeline_events")

    def __repr__(self) -> str:
        return f"<DBTimelineEvent(year={self.year}, impact='{self.impact}')>"
