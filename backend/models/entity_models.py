"""
Entity database models for MapR1
Supports nations, people, companies, and factions
"""

from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.models.db_models import Base


class Entity(Base):
    """Entity model - represents nations, people, companies, factions"""
    
    __tablename__ = "entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # nation, person, company, faction
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    attributes = Column(JSONB, nullable=False, default=dict)  # Flexible JSON attributes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="entities")
    agents = relationship("Agent", back_populates="entity", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Relationship(Base):
    """Relationship between entities"""
    
    __tablename__ = "relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    entity_a_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    entity_b_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # alliance, enemy, trade_partner, neutral, rival
    strength = Column(String(20), nullable=False, default="medium")  # weak, medium, strong
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project")
    entity_a = relationship("Entity", foreign_keys=[entity_a_id])
    entity_b = relationship("Entity", foreign_keys=[entity_b_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "entity_a_id": str(self.entity_a_id),
            "entity_b_id": str(self.entity_b_id),
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
