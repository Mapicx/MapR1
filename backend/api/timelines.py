"""
Timeline API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from backend.core.database import get_db
from backend.repositories.timeline_repository import TimelineRepository
from backend.repositories.scenario_repository import ScenarioRepository


router = APIRouter(tags=["timelines"])


# Request/Response Models

class TimelineCreate(BaseModel):
    """Request model for creating a timeline"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_timeline_id: Optional[str] = None
    branch_point_year: Optional[int] = None
    branch_description: Optional[str] = None


class TimelineUpdate(BaseModel):
    """Request model for updating a timeline"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class TimelineResponse(BaseModel):
    """Response model for timeline"""
    id: str
    project_id: str
    parent_timeline_id: Optional[str]
    name: str
    description: Optional[str]
    branch_point_year: Optional[int]
    branch_description: Optional[str]
    created_at: str
    scenario_count: int = 0


class TimelineBranchRequest(BaseModel):
    """Request model for branching a timeline"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    branch_point_year: int
    branch_description: str
    copy_scenarios: bool = Field(default=True, description="Copy scenarios from parent timeline")


class AddScenarioRequest(BaseModel):
    """Request model for adding scenario to timeline"""
    scenario_id: str
    sequence_order: int = 0


# Timeline Endpoints

@router.post("/projects/{project_id}/timelines", response_model=TimelineResponse)
async def create_timeline(
    project_id: str,
    timeline: TimelineCreate,
    db=Depends(get_db),
):
    """Create a new timeline in a project"""
    try:
        project_uuid = UUID(project_id)
        parent_uuid = UUID(timeline.parent_timeline_id) if timeline.parent_timeline_id else None
        
        repo = TimelineRepository(db)
        
        created_timeline = await repo.create_timeline(
            project_id=project_uuid,
            name=timeline.name,
            description=timeline.description,
            parent_timeline_id=parent_uuid,
            branch_point_year=timeline.branch_point_year,
            branch_description=timeline.branch_description,
        )
        
        logger.info(f"Created timeline: {created_timeline.name}")
        
        response = created_timeline.to_dict()
        response["scenario_count"] = 0
        return TimelineResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to create timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/timelines", response_model=List[TimelineResponse])
async def list_project_timelines(
    project_id: str,
    db=Depends(get_db),
):
    """List all timelines in a project"""
    try:
        project_uuid = UUID(project_id)
        repo = TimelineRepository(db)
        
        timelines = await repo.list_timelines(project_id=project_uuid)
        
        responses = []
        for t in timelines:
            response = t.to_dict()
            response["scenario_count"] = len(t.scenarios) if t.scenarios else 0
            responses.append(TimelineResponse(**response))
        
        return responses
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to list timelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timelines/{timeline_id}", response_model=TimelineResponse)
async def get_timeline(
    timeline_id: str,
    db=Depends(get_db),
):
    """Get timeline by ID"""
    try:
        timeline_uuid = UUID(timeline_id)
        repo = TimelineRepository(db)
        
        timeline = await repo.get_timeline(timeline_uuid)
        if not timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        
        response = timeline.to_dict()
        response["scenario_count"] = len(timeline.scenarios) if timeline.scenarios else 0
        return TimelineResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/timelines/{timeline_id}", response_model=TimelineResponse)
async def update_timeline(
    timeline_id: str,
    timeline_update: TimelineUpdate,
    db=Depends(get_db),
):
    """Update timeline"""
    try:
        timeline_uuid = UUID(timeline_id)
        repo = TimelineRepository(db)
        
        updated_timeline = await repo.update_timeline(
            timeline_id=timeline_uuid,
            name=timeline_update.name,
            description=timeline_update.description,
        )
        
        if not updated_timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        
        logger.info(f"Updated timeline: {updated_timeline.name}")
        
        response = updated_timeline.to_dict()
        response["scenario_count"] = len(updated_timeline.scenarios) if updated_timeline.scenarios else 0
        return TimelineResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/timelines/{timeline_id}")
async def delete_timeline(
    timeline_id: str,
    db=Depends(get_db),
):
    """Delete timeline"""
    try:
        timeline_uuid = UUID(timeline_id)
        repo = TimelineRepository(db)
        
        deleted = await repo.delete_timeline(timeline_uuid)
        if not deleted:
            raise HTTPException(status_code=404, detail="Timeline not found")
        
        logger.info(f"Deleted timeline: {timeline_id}")
        return {"message": "Timeline deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to delete timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/timelines/{timeline_id}/branch", response_model=TimelineResponse)
async def branch_timeline(
    timeline_id: str,
    branch_request: TimelineBranchRequest,
    db=Depends(get_db),
):
    """Create a branch from an existing timeline"""
    try:
        parent_uuid = UUID(timeline_id)
        repo = TimelineRepository(db)
        
        # Get parent timeline
        parent_timeline = await repo.get_timeline(parent_uuid)
        if not parent_timeline:
            raise HTTPException(status_code=404, detail="Parent timeline not found")
        
        # Create branch
        branch = await repo.create_timeline(
            project_id=parent_timeline.project_id,
            name=branch_request.name,
            description=branch_request.description,
            parent_timeline_id=parent_uuid,
            branch_point_year=branch_request.branch_point_year,
            branch_description=branch_request.branch_description,
        )
        
        # Copy scenarios if requested
        if branch_request.copy_scenarios and parent_timeline.scenarios:
            for idx, scenario in enumerate(parent_timeline.scenarios):
                await repo.add_scenario_to_timeline(
                    timeline_id=branch.id,
                    scenario_id=scenario.id,
                    sequence_order=idx,
                )
        
        logger.info(f"Created timeline branch: {branch.name} from {parent_timeline.name}")
        
        # Refresh to get scenarios
        branch = await repo.get_timeline(branch.id)
        response = branch.to_dict()
        response["scenario_count"] = len(branch.scenarios) if branch.scenarios else 0
        return TimelineResponse(**response)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to branch timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/timelines/{timeline_id}/scenarios")
async def add_scenario_to_timeline(
    timeline_id: str,
    request: AddScenarioRequest,
    db=Depends(get_db),
):
    """Add a scenario to a timeline"""
    try:
        timeline_uuid = UUID(timeline_id)
        scenario_uuid = UUID(request.scenario_id)
        
        repo = TimelineRepository(db)
        scenario_repo = ScenarioRepository(db)
        
        # Verify timeline exists
        timeline = await repo.get_timeline(timeline_uuid)
        if not timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        
        # Verify scenario exists
        scenario = await scenario_repo.get_scenario(scenario_uuid)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Add scenario to timeline
        await repo.add_scenario_to_timeline(
            timeline_id=timeline_uuid,
            scenario_id=scenario_uuid,
            sequence_order=request.sequence_order,
        )
        
        logger.info(f"Added scenario {scenario.title} to timeline {timeline.name}")
        return {"message": "Scenario added to timeline successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to add scenario to timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/timelines/{timeline_id}/scenarios/{scenario_id}")
async def remove_scenario_from_timeline(
    timeline_id: str,
    scenario_id: str,
    db=Depends(get_db),
):
    """Remove a scenario from a timeline"""
    try:
        timeline_uuid = UUID(timeline_id)
        scenario_uuid = UUID(scenario_id)
        
        repo = TimelineRepository(db)
        
        removed = await repo.remove_scenario_from_timeline(
            timeline_id=timeline_uuid,
            scenario_id=scenario_uuid,
        )
        
        if not removed:
            raise HTTPException(status_code=404, detail="Scenario not found in timeline")
        
        logger.info(f"Removed scenario from timeline")
        return {"message": "Scenario removed from timeline successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to remove scenario from timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timelines/{timeline_id}/scenarios")
async def get_timeline_scenarios(
    timeline_id: str,
    db=Depends(get_db),
):
    """Get all scenarios in a timeline"""
    try:
        timeline_uuid = UUID(timeline_id)
        repo = TimelineRepository(db)
        scenario_repo = ScenarioRepository(db)
        
        # Get timeline
        timeline = await repo.get_timeline(timeline_uuid)
        if not timeline:
            raise HTTPException(status_code=404, detail="Timeline not found")
        
        # Get scenario details
        scenarios = []
        for scenario in timeline.scenarios:
            scenario_data = await scenario_repo.get_scenario(scenario.id)
            if scenario_data:
                scenarios.append({
                    "id": str(scenario_data.id),
                    "title": scenario_data.title,
                    "description": scenario_data.description,
                    "category": scenario_data.category,
                    "probability": scenario_data.probability,
                })
        
        return {"timeline_id": timeline_id, "scenarios": scenarios}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to get timeline scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))
