"""
Memory API endpoints - Semantic search and pattern recognition
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from backend.memory import get_memory_manager


router = APIRouter(tags=["memory"])


# Request/Response Models

class MemorySearchRequest(BaseModel):
    """Request model for memory search"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")


class MemoryResponse(BaseModel):
    """Response model for a memory"""
    id: str
    content: str
    metadata: dict
    distance: Optional[float] = None


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics"""
    total: int
    scenarios: Optional[int] = None
    events: Optional[int] = None
    entities: Optional[int] = None


# Memory Search Endpoints

@router.post("/projects/{project_id}/memory/search", response_model=List[MemoryResponse])
async def search_memories(
    project_id: str,
    search: MemorySearchRequest,
):
    """
    Search memories using semantic similarity
    
    Finds scenarios, events, and entities similar to the query
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        results = memory_manager.search_all(
            query=search.query,
            project_id=project_uuid,
            top_k=search.top_k,
        )
        
        logger.info(f"Memory search for '{search.query}': found {len(results)} results")
        return [MemoryResponse(**r) for r in results]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/memory/search/scenarios", response_model=List[MemoryResponse])
async def search_similar_scenarios(
    project_id: str,
    search: MemorySearchRequest,
):
    """
    Search for similar scenarios
    
    Useful for finding patterns and recurring themes
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        results = memory_manager.search_similar_scenarios(
            query=search.query,
            project_id=project_uuid,
            top_k=search.top_k,
        )
        
        logger.info(f"Scenario search: found {len(results)} similar scenarios")
        return [MemoryResponse(**r) for r in results]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Scenario search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/memory/search/events", response_model=List[MemoryResponse])
async def search_similar_events(
    project_id: str,
    search: MemorySearchRequest,
):
    """
    Search for similar events
    
    Useful for understanding historical patterns
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        results = memory_manager.search_similar_events(
            query=search.query,
            project_id=project_uuid,
            top_k=search.top_k,
        )
        
        logger.info(f"Event search: found {len(results)} similar events")
        return [MemoryResponse(**r) for r in results]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Event search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/memory", response_model=List[MemoryResponse])
async def get_project_memories(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of memories"),
):
    """
    Get all memories for a project
    
    Returns complete memory history
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        memories = memory_manager.get_world_history(
            project_id=project_uuid,
            limit=limit,
        )
        
        return [MemoryResponse(**m, distance=None) for m in memories]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    project_id: str,
):
    """
    Get memory statistics for a project
    
    Shows counts by type (scenarios, events, entities)
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        stats = memory_manager.get_memory_stats(project_uuid)
        
        return MemoryStatsResponse(**stats)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}/memory")
async def delete_project_memories(
    project_id: str,
):
    """
    Delete all memories for a project
    
    WARNING: This cannot be undone!
    """
    try:
        project_uuid = UUID(project_id)
        memory_manager = get_memory_manager()
        
        count = memory_manager.delete_project_memories(project_uuid)
        
        logger.warning(f"Deleted {count} memories for project {project_id}")
        return {"message": f"Deleted {count} memories", "count": count}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to delete memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))
