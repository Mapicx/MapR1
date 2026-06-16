import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.simulation.simulation_engine import simulation_engine
from backend.theater.theater_models import TensionMetrics, TensionPhase, PacingMode, DivergencePoint, StepNarrative
from backend.theater.tension_tracker import tension_tracker
from backend.theater.pacing_engine import pacing_engine
from backend.theater.divergence_detector import divergence_detector
from backend.theater.narrative_director import narrative_director

class TheaterSession:
    """Holds state for a running theater session."""
    def __init__(self, project_id: uuid.UUID, pacing_mode: PacingMode):
        self.project_id = project_id
        self.pacing_mode = pacing_mode
        self.history: List[TensionMetrics] = []
        self.narratives: List[StepNarrative] = []
        self.divergence_points: List[DivergencePoint] = []
        self.is_running = False
        
        # SSE Event queues for subscribers
        self.subscribers: List[asyncio.Queue] = []
        
    async def broadcast(self, event_type: str, data: Any):
        """Broadcast an event to all connected SSE clients."""
        payload = {"event": event_type, "data": data}
        for q in self.subscribers:
            await q.put(payload)

class SimulationTheater:
    """
    The orchestrator that wraps SimulationEngine with narrative and pacing logic.
    """
    def __init__(self):
        self.sessions: Dict[uuid.UUID, TheaterSession] = {}
        
    def get_or_create_session(self, project_id: uuid.UUID, pacing_mode: PacingMode = PacingMode.AUTO_DRAMATIC) -> TheaterSession:
        if project_id not in self.sessions:
            self.sessions[project_id] = TheaterSession(project_id, pacing_mode)
        return self.sessions[project_id]
        
    def stop_session(self, project_id: uuid.UUID):
        if project_id in self.sessions:
            self.sessions[project_id].is_running = False
            simulation_engine.stop_simulation(project_id)
            
    async def subscribe(self, project_id: uuid.UUID) -> asyncio.Queue:
        session = self.get_or_create_session(project_id)
        q = asyncio.Queue()
        session.subscribers.append(q)
        return q

    async def unsubscribe(self, project_id: uuid.UUID, q: asyncio.Queue):
        if project_id in self.sessions:
            session = self.sessions[project_id]
            if q in session.subscribers:
                session.subscribers.remove(q)

    async def start_theater(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        pacing_mode: PacingMode = PacingMode.AUTO_DRAMATIC,
        max_steps: int = 12
    ):
        """Starts the automated theatrical simulation loop."""
        session = self.get_or_create_session(project_id, pacing_mode)
        session.is_running = True
        simulation_engine.running_simulations[project_id] = True
        
        logger.info(f"Starting Theater Session for {project_id} in {pacing_mode.value} mode")
        await session.broadcast("theater_start", {"project_id": str(project_id), "mode": pacing_mode.value})
        
        step_count = 0
        try:
            while session.is_running and step_count < max_steps:
                step_count += 1
                await session.broadcast("step_start", {"step": step_count})
                
                # 1. Run the raw simulation step
                logger.info(f"Theater executing raw step {step_count}...")
                step_result = await simulation_engine.simulate_step(db, project_id)
                
                # Check for total collapse edge case
                if not getattr(step_result, "success", True) and getattr(step_result, "error", "") == "total_collapse":
                    logger.warning("Theater stopping due to total simulation collapse.")
                    await session.broadcast("theater_complete", {"steps_run": step_count, "reason": "total_collapse"})
                    session.is_running = False
                    break
                    
                world_state = await simulation_engine._get_world_state(db, project_id)
                structured_world = simulation_engine.action_executor._get_structured_state(world_state)
                
                for action in step_result.actions:
                    await session.broadcast("agent_action", {
                        "agent": action.agent_name, 
                        "action": action.action_type, 
                        "success": action.success
                    })
                    
                # Broadcast any new world events generated this step (Black swans, opinions, sabotage)
                new_events = [e for e in structured_world.recent_events if e.step == step_count]
                for event in new_events:
                    await session.broadcast("world_event", {
                        "actor": event.actor,
                        "action": event.action,
                        "outcome": event.outcome,
                        "visibility": event.visibility
                    })
                
                # 2. Compute Tension
                tension = tension_tracker.compute_tension(
                    step=step_count,
                    actions=step_result.actions,
                    world_state=structured_world,
                    history=session.history
                )
                session.history.append(tension)
                
                await session.broadcast("tension_update", {
                    "tension": tension.overall_tension,
                    "phase": tension.phase.value,
                    "is_climax_candidate": tension.is_climax_candidate,
                    "sources": tension.tension_sources
                })
                
                # 3. Narrate the Step (LLM)
                prev_narrative_text = session.narratives[-1].summary if session.narratives else None
                
                # Extract ThemeResolver
                theme_resolver = None
                metadata = structured_world.metadata if hasattr(structured_world, "metadata") else {}
                theme_data = metadata.get("theme")
                if theme_data:
                    from backend.models.compiled_model import CompiledTheme
                    from backend.seeder.theme_resolver import ThemeResolver
                    try:
                        compiled_theme = CompiledTheme(**theme_data)
                        theme_resolver = ThemeResolver(compiled_theme)
                    except Exception as e:
                        logger.error(f"Failed to load CompiledTheme in theater: {e}")

                # Fetch collapsed agents to pass to narrative
                from backend.models.agent_models import Agent
                from sqlalchemy import select
                agent_res = await db.execute(select(Agent).where(Agent.project_id == project_id, Agent.status == "collapsed"))
                collapsed_agents_list = [a.name for a in agent_res.scalars().all()]

                narrative = await narrative_director.narrate_step(
                    step=step_count,
                    actions=step_result.actions,
                    tension=tension,
                    world_state=structured_world,
                    previous_narrative=prev_narrative_text,
                    theme_resolver=theme_resolver,
                    collapsed_agents=collapsed_agents_list,
                )
                session.narratives.append(narrative)
                
                await session.broadcast("narrative", narrative.model_dump())
                
                # 4. Check for Divergence
                divergence = divergence_detector.detect_divergence(
                    step=step_count,
                    actions=step_result.actions,
                    tension=tension,
                    world_state=structured_world
                )
                
                if divergence:
                    session.divergence_points.append(divergence)
                    await session.broadcast("divergence_point", divergence.model_dump())
                
                # 5. Apply Pacing
                pacing = pacing_engine.get_pacing_recommendation(session.pacing_mode, tension, session.history)
                logger.info(f"Pacing recommendation: {pacing.delay_seconds}s delay. Pause: {pacing.should_pause}. Reason: {pacing.reason}")
                
                if pacing.should_pause:
                    logger.info("Theater paused due to pacing recommendation.")
                    await session.broadcast("theater_paused", {"reason": pacing.reason})
                    session.is_running = False # Pause automated loop
                    break
                    
                if pacing.delay_seconds > 0:
                    await asyncio.sleep(pacing.delay_seconds)
                    
        except Exception as e:
            import traceback
            logger.error(f"Theater simulation error: {e}")
            logger.error(f"Theater traceback:\n{traceback.format_exc()}")
            await session.broadcast("error", {"message": str(e)})
        finally:
            session.is_running = False
            simulation_engine.running_simulations[project_id] = False
            await session.broadcast("theater_complete", {"steps_run": step_count})

# Global instance
theater = SimulationTheater()
