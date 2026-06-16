"""
Entity Repository - Data access layer for entities and relationships
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entity_models import Entity, Relationship


class EntityRepository:
    """Repository for entity CRUD operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_entity(
        self,
        project_id: UUID,
        entity_type: str,
        name: str,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """Create a new entity"""
        entity = Entity(
            project_id=project_id,
            type=entity_type,
            name=name,
            description=description,
            attributes=attributes or {},
        )
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_entity(self, entity_id: UUID) -> Optional[Entity]:
        """Get entity by ID"""
        result = await self.session.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalar_one_or_none()
    
    async def list_entities(
        self,
        project_id: Optional[UUID] = None,
        entity_type: Optional[str] = None,
    ) -> List[Entity]:
        """List entities with optional filters"""
        query = select(Entity)
        
        conditions = []
        if project_id:
            conditions.append(Entity.project_id == project_id)
        if entity_type:
            conditions.append(Entity.type == entity_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_entity(
        self,
        entity_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Optional[Entity]:
        """Update entity"""
        entity = await self.get_entity(entity_id)
        if not entity:
            return None
        
        if name is not None:
            entity.name = name
        if description is not None:
            entity.description = description
        if attributes is not None:
            entity.attributes = attributes
        
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete_entity(self, entity_id: UUID) -> bool:
        """Delete entity"""
        entity = await self.get_entity(entity_id)
        if not entity:
            return False
        
        await self.session.delete(entity)
        await self.session.commit()
        return True
    
    # Relationship methods
    
    async def create_relationship(
        self,
        project_id: UUID,
        entity_a_id: UUID,
        entity_b_id: UUID,
        relationship_type: str,
        strength: str = "medium",
        description: Optional[str] = None,
    ) -> Relationship:
        """Create relationship between two entities"""
        relationship = Relationship(
            project_id=project_id,
            entity_a_id=entity_a_id,
            entity_b_id=entity_b_id,
            relationship_type=relationship_type,
            strength=strength,
            description=description,
        )
        self.session.add(relationship)
        await self.session.commit()
        await self.session.refresh(relationship)
        return relationship
    
    async def get_relationship(self, relationship_id: UUID) -> Optional[Relationship]:
        """Get relationship by ID"""
        result = await self.session.execute(
            select(Relationship).where(Relationship.id == relationship_id)
        )
        return result.scalar_one_or_none()
    
    async def list_relationships(
        self,
        project_id: Optional[UUID] = None,
        entity_id: Optional[UUID] = None,
    ) -> List[Relationship]:
        """List relationships with optional filters"""
        query = select(Relationship)
        
        conditions = []
        if project_id:
            conditions.append(Relationship.project_id == project_id)
        if entity_id:
            conditions.append(
                (Relationship.entity_a_id == entity_id) | (Relationship.entity_b_id == entity_id)
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_relationship(
        self,
        relationship_id: UUID,
        relationship_type: Optional[str] = None,
        strength: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Relationship]:
        """Update relationship"""
        relationship = await self.get_relationship(relationship_id)
        if not relationship:
            return None
        
        if relationship_type is not None:
            relationship.relationship_type = relationship_type
        if strength is not None:
            relationship.strength = strength
        if description is not None:
            relationship.description = description
        
        await self.session.commit()
        await self.session.refresh(relationship)
        return relationship
    
    async def delete_relationship(self, relationship_id: UUID) -> bool:
        """Delete relationship"""
        relationship = await self.get_relationship(relationship_id)
        if not relationship:
            return False
        
        await self.session.delete(relationship)
        await self.session.commit()
        return True
