from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from backend.models.db_models import Base

class ScheduledEvent(Base):
    """Time bomb: triggered on a future simulation step"""
    __tablename__ = "scheduled_events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    trigger_turn = Column(Integer, nullable=False)  # Simulation step to fire
    event_type = Column(String(100), nullable=False)  # "market_crash", "regulatory_backlash", "accident", etc.
    description = Column(Text)
    cause_action_id = Column(PGUUID(as_uuid=True), nullable=True)

    # payload for the consequence
    impact_data = Column(JSONB, default=dict)  # e.g. {"public_opinion": {"topic": +0.05}, "market_conditions": {"sector": -0.3}}
    visibility = Column(Float, default=0.5)

    created_at = Column(DateTime, default=datetime.utcnow)
    fired_at = Column(DateTime, nullable=True)
    is_fired = Column(Boolean, default=False)
