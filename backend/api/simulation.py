"""
Simulation API Endpoints

Controls simulation execution and pattern detection.
"""

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from backend.core.database import get_db
from backend.repositories.project_repository import ProjectRepository
from backend.models.action_models import (
    SimulationStepResult,
    SimulationControlRequest,
    PatternDetectionRequest,
    PatternResponse,
    ActionResponse,
)
from backend.models.action_models import AgentAction, EmergentPattern
from backend.simulation.simulation_engine import simulation_engine


router = APIRouter()


# ============================================================================
# Simulation Control
# ============================================================================

@router.post("/projects/{project_id}/simulate/step", response_model=SimulationStepResult)
async def simulate_step(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Run one simulation step.
    
    Process:
    1. Each agent perceives the world
    2. Each agent makes a decision (LLM)
    3. Actions are executed (full execution)
    4. World state is updated
    5. Patterns are detected (LLM)
    """
    logger.info(f"Running simulation step for project {project_id}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Run simulation step
    try:
        result = await simulation_engine.simulate_step(db, project_id)
        logger.info(f"Simulation step completed: {len(result.actions)} actions")
        return result
    except Exception as e:
        logger.error(f"Simulation step failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/projects/{project_id}/simulate/start")
async def start_simulation(
    project_id: UUID,
    control: SimulationControlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Start automatic simulation.
    
    Runs in the background for the specified number of steps.
    """
    logger.info(f"Starting auto-simulation for project {project_id}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if already running
    if simulation_engine.is_running(project_id):
        raise HTTPException(status_code=400, detail="Simulation already running")
    
    # Start simulation in background
    max_steps = control.max_steps or 10
    step_delay = control.step_delay
    
    # Note: Background tasks in FastAPI don't work well with async DB sessions
    # For production, use Celery or similar task queue
    # For now, we'll just start it and return immediately
    
    logger.warning("Auto-simulation started but will run synchronously (use task queue for production)")
    
    try:
        result = await simulation_engine.run_auto_simulation(
            db,
            project_id=project_id,
            max_steps=max_steps,
            step_delay=step_delay,
        )
        return result
    except Exception as e:
        logger.error(f"Auto-simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/projects/{project_id}/simulate/stop")
async def stop_simulation(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Stop automatic simulation"""
    logger.info(f"Stopping simulation for project {project_id}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Stop simulation
    simulation_engine.stop_simulation(project_id)
    
    return {"message": "Simulation stopped", "project_id": str(project_id)}


@router.get("/projects/{project_id}/simulate/status")
async def get_simulation_status(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current simulation status"""
    logger.info(f"Getting simulation status for project {project_id}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get status
    status = await simulation_engine.get_simulation_status(db, project_id)
    
    return status


# ============================================================================
# Pattern Detection
# ============================================================================

@router.post("/projects/{project_id}/patterns/detect", response_model=List[PatternResponse])
async def detect_patterns(
    project_id: UUID,
    request: PatternDetectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Detect emergent patterns using LLM.
    
    Analyzes:
    - All entities and agents
    - All scenarios and timeline events
    - Recent actions and world events
    - All relationships and interactions
    """
    logger.info(f"Detecting patterns for project {project_id}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Detect patterns
    try:
        patterns = await simulation_engine.pattern_detector.detect_patterns(
            db,
            project_id=project_id,
            time_window=request.time_window,
            min_significance=request.min_significance,
        )
        
        logger.info(f"Detected {len(patterns)} patterns")
        return patterns
    except Exception as e:
        logger.error(f"Pattern detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern detection failed: {str(e)}")


@router.get("/projects/{project_id}/patterns", response_model=List[PatternResponse])
async def list_patterns(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all detected patterns for a project"""
    logger.info(f"Listing patterns for project {project_id}")
    
    result = await db.execute(
        select(EmergentPattern)
        .where(EmergentPattern.project_id == project_id)
        .order_by(EmergentPattern.significance.desc())
    )
    patterns = list(result.scalars().all())
    
    logger.info(f"Found {len(patterns)} patterns")
    return patterns


@router.get("/patterns/{pattern_id}", response_model=PatternResponse)
async def get_pattern(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get pattern by ID"""
    result = await db.execute(
        select(EmergentPattern).where(EmergentPattern.id == pattern_id)
    )
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return pattern


# ============================================================================
# Simulation History
# ============================================================================

@router.get("/projects/{project_id}/simulation/history", response_model=List[ActionResponse])
async def get_simulation_history(
    project_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get simulation history (recent actions)"""
    logger.info(f"Getting simulation history for project {project_id}")
    
    result = await db.execute(
        select(AgentAction)
        .where(AgentAction.project_id == project_id)
        .order_by(AgentAction.created_at.desc())
        .limit(limit)
    )
    actions = list(result.scalars().all())
    
    # Convert to response format
    responses = []
    for action in actions:
        # Get agent name
        from backend.models.agent_models import Agent
        agent_result = await db.execute(
            select(Agent).where(Agent.id == action.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        responses.append(ActionResponse(
            id=action.id,
            agent_id=action.agent_id,
            agent_name=agent.name if agent else "Unknown",
            action_type=action.action_type,
            description=action.description,
            reasoning=action.reasoning,
            confidence=action.confidence,
            executed=action.executed,
            success=action.success,
            outcome=action.outcome,
            impact=action.impact,
            simulation_step=action.simulation_step,
            created_at=action.created_at,
        ))
    
    logger.info(f"Found {len(responses)} actions")
    return responses
