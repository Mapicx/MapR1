"""
MapR1 — Projects API
Endpoints for project/world management.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.repositories.project_repository import ProjectRepository

router = APIRouter(prefix="/projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    """Request to create a project"""

    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Request to update a project"""

    name: Optional[str] = None
    description: Optional[str] = None


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Create a new project/world for organizing scenarios",
)
async def create_project(request: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project"""
    try:
        repo = ProjectRepository(db)
        project = await repo.create_project(name=request.name, description=request.description)
        await db.commit()

        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.get(
    "",
    response_model=List[dict],
    summary="List Projects",
    description="List all projects with pagination",
)
async def list_projects(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """List all projects"""
    try:
        repo = ProjectRepository(db)
        projects = await repo.list_projects(limit=limit, offset=offset)

        result = []
        for project in projects:
            # Get stats for each project
            stats = await repo.get_project_stats(project.id)

            result.append(
                {
                    "id": str(project.id),
                    "name": project.name,
                    "description": project.description,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                    "stats": stats,
                }
            )

        return result

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}",
        )


@router.get(
    "/{project_id}",
    response_model=dict,
    summary="Get Project",
    description="Get a specific project with statistics",
)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get project by ID"""
    try:
        repo = ProjectRepository(db)
        project = await repo.get_project(uuid.UUID(project_id))

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Get stats
        stats = await repo.get_project_stats(project.id)

        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}",
        )


@router.put(
    "/{project_id}",
    response_model=dict,
    summary="Update Project",
    description="Update project name or description",
)
async def update_project(
    project_id: str, request: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    """Update project"""
    try:
        repo = ProjectRepository(db)
        project = await repo.update_project(
            project_id=uuid.UUID(project_id), name=request.name, description=request.description
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        await db.commit()

        return {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "updated_at": project.updated_at.isoformat(),
            "message": "Project updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Project",
    description="Delete a project and all associated scenarios",
)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete project (cascade deletes scenarios)"""
    try:
        repo = ProjectRepository(db)
        deleted = await repo.delete_project(uuid.UUID(project_id))

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        await db.commit()
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )


@router.get(
    "/{project_id}/scenarios",
    response_model=List[dict],
    summary="Get Project Scenarios",
    description="Get all scenarios for a specific project",
)
async def get_project_scenarios(
    project_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Get all scenarios for a project"""
    try:
        repo = ProjectRepository(db)

        # Verify project exists
        project = await repo.get_project(uuid.UUID(project_id))
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Get scenarios
        scenarios = await repo.get_project_scenarios(uuid.UUID(project_id), limit=limit)

        result = []
        for scenario in scenarios:
            result.append(
                {
                    "id": str(scenario.id),
                    "title": scenario.title,
                    "description": scenario.description,
                    "category": scenario.category,
                    "probability": scenario.probability,
                    "saved": scenario.saved,
                    "created_at": scenario.created_at.isoformat(),
                    "timeline_events_count": len(scenario.timeline_events),
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project scenarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scenarios: {str(e)}",
        )


@router.get(
    "/{project_id}/world-state",
    response_model=dict,
    summary="Get World State",
    description="Get current world state metrics for a project",
)
async def get_world_state(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get world state for a project"""
    try:
        from sqlalchemy import select, func
        from backend.models.entity_models import Entity
        from backend.models.agent_models import Agent
        
        repo = ProjectRepository(db)

        # Verify project exists
        project = await repo.get_project(uuid.UUID(project_id))
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

        # Get stats
        stats = await repo.get_project_stats(project.id)
        
        # Get entity type counts
        entity_type_counts = await db.execute(
            select(Entity.type, func.count(Entity.id))
            .where(Entity.project_id == project.id)
            .group_by(Entity.type)
        )
        entity_types = {row[0]: row[1] for row in entity_type_counts}

        total_entities = stats.get("entities", 0)
        total_agents = stats.get("agents", 0)
        
        # Simple heuristics for world state
        # These would be computed from actual simulation data in production
        stability = 0.65 if total_agents < 10 else 0.45
        economy = 0.72 if total_entities > 2 else 0.55
        technology_level = 0.58
        active_conflicts = 0  # Would be computed from agent relationships

        return {
            "project_id": str(project.id),
            "current_step": 0,  # Would come from simulation state
            "stability": stability,
            "economy": economy,
            "technology_level": technology_level,
            "active_conflicts": active_conflicts,
            "total_agents": total_agents,
            "total_entities": total_entities,
            "entity_types": entity_types,  # e.g., {"nation": 1, "company": 0}
            "recent_events": [],  # Would come from action history
            "updated_at": project.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get world state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve world state: {str(e)}",
        )

