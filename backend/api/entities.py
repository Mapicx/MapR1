"""
Entity API endpoints
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from backend.core.database import get_db
from backend.repositories.entity_repository import EntityRepository
from backend.memory import get_memory_manager


router = APIRouter(tags=["entities"])


# Request/Response Models

class EntityCreate(BaseModel):
    """Request model for creating an entity"""
    type: str = Field(..., description="Entity type: nation, person, company, faction")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class EntityUpdate(BaseModel):
    """Request model for updating an entity"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class EntityResponse(BaseModel):
    """Response model for entity"""
    id: str
    project_id: str
    type: str
    name: str
    description: Optional[str]
    attributes: Dict[str, Any]
    created_at: str
    updated_at: str


class RelationshipCreate(BaseModel):
    """Request model for creating a relationship"""
    entity_a_id: str
    entity_b_id: str
    relationship_type: str = Field(..., description="alliance, enemy, trade_partner, neutral, rival")
    strength: str = Field(default="medium", description="weak, medium, strong")
    description: Optional[str] = None


class RelationshipUpdate(BaseModel):
    """Request model for updating a relationship"""
    relationship_type: Optional[str] = None
    strength: Optional[str] = None
    description: Optional[str] = None


class RelationshipResponse(BaseModel):
    """Response model for relationship"""
    id: str
    project_id: str
    entity_a_id: str
    entity_b_id: str
    relationship_type: str
    strength: str
    description: Optional[str]
    created_at: str
    updated_at: str


# Entity Endpoints

@router.post("/projects/{project_id}/entities", response_model=EntityResponse)
async def create_entity(
    project_id: str,
    entity: EntityCreate,
    db=Depends(get_db),
):
    """Create a new entity in a project"""
    try:
        project_uuid = UUID(project_id)
        repo = EntityRepository(db)
        
        # Validate entity type
        valid_types = ["nation", "person", "company", "faction"]
        if entity.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
            )
        
        created_entity = await repo.create_entity(
            project_id=project_uuid,
            entity_type=entity.type,
            name=entity.name,
            description=entity.description,
            attributes=entity.attributes,
        )
        
        # Store in memory for semantic search
        try:
            memory_manager = get_memory_manager()
            memory_manager.store_entity(
                project_id=project_uuid,
                entity_id=created_entity.id,
                entity_type=created_entity.type,
                name=created_entity.name,
                description=created_entity.description,
                attributes=created_entity.attributes,
            )
        except Exception as mem_error:
            logger.warning(f"Failed to store entity in memory: {mem_error}")
        
        logger.info(f"Created entity: {created_entity.name} ({created_entity.type})")
        return EntityResponse(**created_entity.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/entities", response_model=List[EntityResponse])
async def list_project_entities(
    project_id: str,
    entity_type: Optional[str] = None,
    db=Depends(get_db),
):
    """List all entities in a project"""
    try:
        project_uuid = UUID(project_id)
        repo = EntityRepository(db)
        
        entities = await repo.list_entities(
            project_id=project_uuid,
            entity_type=entity_type,
        )
        
        return [EntityResponse(**e.to_dict()) for e in entities]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    db=Depends(get_db),
):
    """Get entity by ID"""
    try:
        entity_uuid = UUID(entity_id)
        repo = EntityRepository(db)
        
        entity = await repo.get_entity(entity_uuid)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return EntityResponse(**entity.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entities/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: str,
    entity_update: EntityUpdate,
    db=Depends(get_db),
):
    """Update entity"""
    try:
        entity_uuid = UUID(entity_id)
        repo = EntityRepository(db)
        
        updated_entity = await repo.update_entity(
            entity_id=entity_uuid,
            name=entity_update.name,
            description=entity_update.description,
            attributes=entity_update.attributes,
        )
        
        if not updated_entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        logger.info(f"Updated entity: {updated_entity.name}")
        return EntityResponse(**updated_entity.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: str,
    db=Depends(get_db),
):
    """Delete entity"""
    try:
        entity_uuid = UUID(entity_id)
        repo = EntityRepository(db)
        
        deleted = await repo.delete_entity(entity_uuid)
        if not deleted:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        logger.info(f"Deleted entity: {entity_id}")
        return {"message": "Entity deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to delete entity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Relationship Endpoints

@router.post("/relationships", response_model=RelationshipResponse)
async def create_relationship(
    relationship: RelationshipCreate,
    project_id: str,
    db=Depends(get_db),
):
    """Create a relationship between two entities"""
    try:
        project_uuid = UUID(project_id)
        entity_a_uuid = UUID(relationship.entity_a_id)
        entity_b_uuid = UUID(relationship.entity_b_id)
        
        repo = EntityRepository(db)
        
        # Validate relationship type
        valid_types = ["alliance", "enemy", "trade_partner", "neutral", "rival"]
        if relationship.relationship_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate strength
        valid_strengths = ["weak", "medium", "strong"]
        if relationship.strength not in valid_strengths:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strength. Must be one of: {', '.join(valid_strengths)}"
            )
        
        created_relationship = await repo.create_relationship(
            project_id=project_uuid,
            entity_a_id=entity_a_uuid,
            entity_b_id=entity_b_uuid,
            relationship_type=relationship.relationship_type,
            strength=relationship.strength,
            description=relationship.description,
        )
        
        logger.info(f"Created relationship: {relationship.relationship_type}")
        return RelationshipResponse(**created_relationship.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/relationships", response_model=List[RelationshipResponse])
async def list_project_relationships(
    project_id: str,
    entity_id: Optional[str] = None,
    db=Depends(get_db),
):
    """List all relationships in a project"""
    try:
        project_uuid = UUID(project_id)
        entity_uuid = UUID(entity_id) if entity_id else None
        
        repo = EntityRepository(db)
        
        relationships = await repo.list_relationships(
            project_id=project_uuid,
            entity_id=entity_uuid,
        )
        
        return [RelationshipResponse(**r.to_dict()) for r in relationships]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to list relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/relationships/{relationship_id}", response_model=RelationshipResponse)
async def update_relationship(
    relationship_id: str,
    relationship_update: RelationshipUpdate,
    db=Depends(get_db),
):
    """Update relationship"""
    try:
        relationship_uuid = UUID(relationship_id)
        repo = EntityRepository(db)
        
        updated_relationship = await repo.update_relationship(
            relationship_id=relationship_uuid,
            relationship_type=relationship_update.relationship_type,
            strength=relationship_update.strength,
            description=relationship_update.description,
        )
        
        if not updated_relationship:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        logger.info(f"Updated relationship: {relationship_id}")
        return RelationshipResponse(**updated_relationship.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: str,
    db=Depends(get_db),
):
    """Delete relationship"""
    try:
        relationship_uuid = UUID(relationship_id)
        repo = EntityRepository(db)
        
        deleted = await repo.delete_relationship(relationship_uuid)
        if not deleted:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        logger.info(f"Deleted relationship: {relationship_id}")
        return {"message": "Relationship deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))
