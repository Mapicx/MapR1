import uuid
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from backend.core.database import get_db
from backend.theater.simulation_theater import theater
from backend.theater.theater_models import PacingMode, InjectedEvent
from backend.theater.event_injector import event_injector

router = APIRouter(prefix="/api/theater", tags=["Simulation Theater"])

class TheaterStartRequest(BaseModel):
    pacing_mode: PacingMode = PacingMode.AUTO_DRAMATIC
    max_steps: int = 12

@router.post("/{project_id}/start")
async def start_theater(
    project_id: uuid.UUID,
    request: TheaterStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start an automated theatrical simulation session."""
    if project_id in theater.sessions and theater.sessions[project_id].is_running:
        raise HTTPException(status_code=400, detail="Theater is already running for this project.")
        
    # Start in background task so API can return immediately
    asyncio.create_task(
        theater.start_theater(db, project_id, request.pacing_mode, request.max_steps)
    )
    
    return {"message": f"Theater started for project {project_id}", "mode": request.pacing_mode.value}

@router.post("/{project_id}/stop")
async def stop_theater(project_id: uuid.UUID):
    """Stop an automated theatrical simulation session."""
    theater.stop_session(project_id)
    return {"message": f"Theater stopped for project {project_id}"}

@router.post("/{project_id}/inject")
async def inject_event(
    project_id: uuid.UUID,
    event: InjectedEvent,
    step: int = 0, # Assuming current step or user specifies
    db: AsyncSession = Depends(get_db)
):
    """Inject an external event into the running simulation."""
    result = await event_injector.inject(db, project_id, event, step)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
        
    # Also broadcast the injection to SSE clients
    session = theater.get_or_create_session(project_id)
    await session.broadcast("event_injected", event.model_dump())
        
    return {"message": "Event injected successfully"}

@router.get("/{project_id}/state")
async def get_theater_state(project_id: uuid.UUID):
    """Get the current state of the theater session."""
    if project_id not in theater.sessions:
        return {"is_running": False, "narratives": [], "history": [], "divergences": []}
        
    session = theater.sessions[project_id]
    return {
        "is_running": session.is_running,
        "pacing_mode": session.pacing_mode.value,
        "current_tension": session.history[-1].overall_tension if session.history else 0,
        "narratives_count": len(session.narratives),
        "divergences_count": len(session.divergence_points)
    }

async def sse_generator(project_id: uuid.UUID, request: Request):
    """Generator for Server-Sent Events."""
    queue = await theater.subscribe(project_id)
    try:
        while True:
            if await request.is_disconnected():
                break
                
            # Wait for next event from theater
            payload = await queue.get()
            event_type = payload["event"]
            data = json.dumps(payload["data"])
            
            # Format as SSE
            yield f"event: {event_type}\ndata: {data}\n\n"
            queue.task_done()
            
    except asyncio.CancelledError:
        pass
    finally:
        await theater.unsubscribe(project_id, queue)

@router.get("/{project_id}/stream")
async def theater_stream(project_id: uuid.UUID, request: Request):
    """Subscribe to the real-time Server-Sent Events stream for the theater."""
    return StreamingResponse(
        sse_generator(project_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
