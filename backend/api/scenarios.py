"""
MapR1 — Scenarios API
Endpoints for scenario generation and management.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.scenario import Scenario, ScenarioRequest, ScenarioResponse
from backend.reasoning.scenario_generator import scenario_generator
from backend.repositories.scenario_repository import ScenarioRepository
from backend.memory import get_memory_manager

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.post(
    "/generate",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Future Scenarios",
    description="Generate multiple alternate future scenarios and optionally save to database",
)
async def generate_scenarios(
    request: ScenarioRequest,
    project_id: Optional[str] = Query(None, description="Project ID to associate scenarios with"),
    save: bool = Query(True, description="Save scenarios to database"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate future scenarios based on user input.
    
    Scenarios are automatically saved to database (with saved=false) unless save=false.
    Use POST /scenarios/{id}/save to mark as explicitly saved.
    """
    try:
        logger.info(f"Received scenario request: {request.prompt[:50]}...")

        # Generate scenarios
        scenarios = await scenario_generator.generate_scenarios(
            user_input=request.prompt, num_scenarios=request.num_scenarios
        )

        if not scenarios:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate scenarios. Please try again.",
            )

        # Create response
        response = ScenarioResponse(
            prompt=request.prompt,
            scenarios=scenarios,
            model_used="qwen3.5:4b",
        )

        # Save to database if requested
        db_ids = []
        if save:
            try:
                repo = ScenarioRepository(db)
                memory_manager = get_memory_manager()
                project_uuid = uuid.UUID(project_id) if project_id else None

                for scenario in scenarios:
                    db_scenario = await repo.create_scenario(
                        scenario=scenario,
                        prompt=request.prompt,
                        request_id=uuid.UUID(response.request_id),
                        model_used=response.model_used,
                        project_id=project_uuid,
                        saved=False,  # Auto-saved but not explicitly saved by user
                    )
                    db_ids.append(str(db_scenario.id))
                    
                    # Store in memory for semantic search
                    if project_uuid:
                        try:
                            memory_manager.store_scenario(
                                project_id=project_uuid,
                                scenario_id=db_scenario.id,
                                title=scenario.title,
                                description=scenario.description,
                                category=scenario.category,
                                timeline_events=[
                                    {
                                        "year": e.year,
                                        "description": e.description,
                                        "impact": e.impact,
                                    }
                                    for e in scenario.timeline
                                ],
                            )
                        except Exception as mem_error:
                            logger.warning(f"Failed to store scenario in memory: {mem_error}")

                await db.commit()
                logger.success(f"Saved {len(db_ids)} scenarios to database and memory")

            except Exception as e:
                logger.error(f"Failed to save scenarios to database: {e}")
                await db.rollback()
                # Continue anyway - generation succeeded

        logger.success(f"Generated {len(scenarios)} scenarios successfully")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during scenario generation: {str(e)}",
        )


@router.get(
    "",
    response_model=List[dict],
    summary="List Scenarios",
    description="List all scenarios with optional filters",
)
async def list_scenarios(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    saved_only: bool = Query(False, description="Only return saved scenarios"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """List scenarios with optional filtering"""
    try:
        repo = ScenarioRepository(db)
        project_uuid = uuid.UUID(project_id) if project_id else None

        scenarios = await repo.list_scenarios(
            project_id=project_uuid, saved_only=saved_only, limit=limit, offset=offset
        )

        # Convert to dict for response
        result = []
        for scenario in scenarios:
            result.append(
                {
                    "id": str(scenario.id),
                    "project_id": str(scenario.project_id) if scenario.project_id else None,
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

    except Exception as e:
        logger.error(f"Failed to list scenarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scenarios: {str(e)}",
        )


@router.get(
    "/{scenario_id}",
    response_model=dict,
    summary="Get Scenario",
    description="Get a specific scenario with full timeline",
)
async def get_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Get scenario by ID with full details"""
    try:
        repo = ScenarioRepository(db)
        scenario = await repo.get_scenario(uuid.UUID(scenario_id))

        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found"
            )

        # Convert to dict
        return {
            "id": str(scenario.id),
            "project_id": str(scenario.project_id) if scenario.project_id else None,
            "prompt": scenario.prompt,
            "title": scenario.title,
            "description": scenario.description,
            "category": scenario.category,
            "probability": scenario.probability,
            "model_used": scenario.model_used,
            "saved": scenario.saved,
            "created_at": scenario.created_at.isoformat(),
            "timeline": [
                {
                    "year": event.year,
                    "description": event.description,
                    "impact": event.impact,
                }
                for event in sorted(scenario.timeline_events, key=lambda e: e.sequence_order)
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scenario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scenario: {str(e)}",
        )


@router.post(
    "/{scenario_id}/save",
    response_model=dict,
    summary="Save Scenario",
    description="Mark a scenario as explicitly saved by user",
)
async def save_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Mark scenario as saved"""
    try:
        repo = ScenarioRepository(db)
        scenario = await repo.mark_as_saved(uuid.UUID(scenario_id))

        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found"
            )

        await db.commit()

        return {
            "id": str(scenario.id),
            "title": scenario.title,
            "saved": scenario.saved,
            "message": "Scenario marked as saved",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save scenario: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save scenario: {str(e)}",
        )


@router.delete(
    "/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Scenario",
    description="Delete a scenario and its timeline events",
)
async def delete_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """Delete scenario"""
    try:
        repo = ScenarioRepository(db)
        deleted = await repo.delete_scenario(uuid.UUID(scenario_id))

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found"
            )

        await db.commit()
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scenario: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete scenario: {str(e)}",
        )


@router.get(
    "/search",
    response_model=List[dict],
    summary="Search Scenarios",
    description="Search scenarios by title or description",
)
async def search_scenarios(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """Search scenarios"""
    try:
        repo = ScenarioRepository(db)
        scenarios = await repo.search_scenarios(q, limit)

        result = []
        for scenario in scenarios:
            result.append(
                {
                    "id": str(scenario.id),
                    "title": scenario.title,
                    "description": scenario.description,
                    "category": scenario.category,
                    "saved": scenario.saved,
                    "created_at": scenario.created_at.isoformat(),
                }
            )

        return result

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )
