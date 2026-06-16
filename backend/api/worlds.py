"""
World State API endpoints
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from loguru import logger

from backend.core.database import get_db
from backend.world_state.world_manager import WorldManager
from backend.memory import get_memory_manager


router = APIRouter(tags=["worlds"])


# Request/Response Models

class WorldStateCreate(BaseModel):
    """Request model for creating world state"""
    initial_state: Dict[str, Any] = Field(default_factory=dict)


class WorldStateUpdate(BaseModel):
    """Request model for updating world state"""
    state_updates: Dict[str, Any]


class WorldStateResponse(BaseModel):
    """Response model for world state"""
    id: str
    project_id: str
    state: Dict[str, Any]
    last_updated: str
    created_at: str


class WorldEventCreate(BaseModel):
    """Request model for creating world event"""
    event_type: str = Field(..., description="war, treaty, discovery, disaster, etc.")
    description: str
    impact_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Impact from -1.0 (negative) to 1.0 (positive)")
    affected_entity_ids: List[str] = Field(default_factory=list)
    occurred_at: Optional[str] = None  # ISO format datetime


class WorldEventResponse(BaseModel):
    """Response model for world event"""
    id: str
    world_state_id: str
    event_type: str
    description: str
    impact_score: Optional[float]
    affected_entity_ids: List[str]
    occurred_at: str
    created_at: str


class WorldSnapshotResponse(BaseModel):
    """Response model for complete world snapshot"""
    state: Dict[str, Any]
    recent_events: List[WorldEventResponse]
    last_updated: Optional[str]


# World State Endpoints

@router.post("/projects/{project_id}/world", response_model=WorldStateResponse)
async def create_world_state(
    project_id: str,
    world_state: WorldStateCreate,
    db=Depends(get_db),
):
    """Create world state for a project"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        # Check if world state already exists
        existing = await manager.get_world_state(project_uuid)
        if existing:
            raise HTTPException(status_code=400, detail="World state already exists for this project")
        
        created_state = await manager.create_world_state(
            project_id=project_uuid,
            initial_state=world_state.initial_state,
        )
        
        logger.info(f"Created world state for project: {project_id}")
        return WorldStateResponse(**created_state.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create world state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/world", response_model=WorldStateResponse)
async def get_world_state(
    project_id: str,
    db=Depends(get_db),
):
    """Get world state for a project"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        world_state = await manager.get_world_state(project_uuid)
        if not world_state:
            raise HTTPException(status_code=404, detail="World state not found")
        
        return WorldStateResponse(**world_state.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get world state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/world", response_model=WorldStateResponse)
async def update_world_state(
    project_id: str,
    update: WorldStateUpdate,
    db=Depends(get_db),
):
    """Update world state (merges with existing state)"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        updated_state = await manager.update_world_state(
            project_id=project_uuid,
            state_updates=update.state_updates,
        )
        
        if not updated_state:
            raise HTTPException(status_code=404, detail="World state not found")
        
        logger.info(f"Updated world state for project: {project_id}")
        return WorldStateResponse(**updated_state.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update world state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/world/snapshot", response_model=WorldSnapshotResponse)
async def get_world_snapshot(
    project_id: str,
    db=Depends(get_db),
):
    """Get complete world snapshot including state and recent events"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        snapshot = await manager.get_world_snapshot(project_uuid)
        
        return WorldSnapshotResponse(
            state=snapshot["state"],
            recent_events=[WorldEventResponse(**e) for e in snapshot["recent_events"]],
            last_updated=snapshot["last_updated"],
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get world snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# World Event Endpoints

@router.post("/projects/{project_id}/events", response_model=WorldEventResponse)
async def record_world_event(
    project_id: str,
    event: WorldEventCreate,
    db=Depends(get_db),
):
    """Record a world event"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        # Parse affected entity IDs
        affected_uuids = [UUID(eid) for eid in event.affected_entity_ids] if event.affected_entity_ids else None
        
        # Parse occurred_at if provided
        occurred_at = datetime.fromisoformat(event.occurred_at) if event.occurred_at else None
        
        created_event = await manager.record_event(
            project_id=project_uuid,
            event_type=event.event_type,
            description=event.description,
            impact_score=event.impact_score,
            affected_entity_ids=affected_uuids,
            occurred_at=occurred_at,
        )
        
        # Store in memory for semantic search
        try:
            memory_manager = get_memory_manager()
            memory_manager.store_event(
                project_id=project_uuid,
                event_id=created_event.id,
                event_type=created_event.event_type,
                description=created_event.description,
                impact_score=created_event.impact_score,
            )
        except Exception as mem_error:
            logger.warning(f"Failed to store event in memory: {mem_error}")
        
        logger.info(f"Recorded world event: {event.event_type} for project {project_id}")
        return WorldEventResponse(**created_event.to_dict())
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID or datetime: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to record world event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/events", response_model=List[WorldEventResponse])
async def get_world_events(
    project_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db=Depends(get_db),
):
    """Get world events with optional filters"""
    try:
        project_uuid = UUID(project_id)
        manager = WorldManager(db)
        
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        events = await manager.get_events(
            project_id=project_uuid,
            start_date=start_dt,
            end_date=end_dt,
            event_type=event_type,
        )
        
        return [WorldEventResponse(**e.to_dict()) for e in events]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID or datetime: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get world events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
