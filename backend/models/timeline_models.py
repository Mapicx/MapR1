"""
Timeline branching models for MapR1
Supports alternate timelines and timeline comparisons
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.models.db_models import Base


class Timeline(Base):
    """Timeline model - represents a timeline or alternate reality"""
    
    __tablename__ = "timelines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_timeline_id = Column(UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    branch_point_year = Column(Integer, nullable=True)  # Year where this timeline branched
    branch_description = Column(Text, nullable=True)  # What caused the branch
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="timelines")
    parent_timeline = relationship("Timeline", remote_side=[id], backref="child_timelines")
    scenarios = relationship("DBScenario", secondary="timeline_scenarios", back_populates="timelines")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "parent_timeline_id": str(self.parent_timeline_id) if self.parent_timeline_id else None,
            "name": self.name,
            "description": self.description,
            "branch_point_year": self.branch_point_year,
            "branch_description": self.branch_description,
            "created_at": self.created_at.isoformat(),
        }


class TimelineScenario(Base):
    """Association table linking timelines to scenarios"""
    
    __tablename__ = "timeline_scenarios"
    
    timeline_id = Column(UUID(as_uuid=True), ForeignKey("timelines.id", ondelete="CASCADE"), primary_key=True)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), primary_key=True)
    sequence_order = Column(Integer, nullable=False, default=0)  # Order of scenario in timeline
    created_at = Column(DateTime, default=datetime.utcnow)
