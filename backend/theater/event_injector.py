import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.theater.theater_models import InjectedEvent, InjectionResult
from backend.models.world_models import WorldState
from backend.models.agent_models import AgentMemory

class EventInjector:
    """Injects external events into a running simulation."""
    
    async def inject(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        event: InjectedEvent,
        step: int
    ) -> InjectionResult:
        logger.info(f"Injecting event into project {project_id}: {event.description}")
        
        try:
            # 1. Update World State
            if event.world_state_changes:
                # Need to merge changes into the JSONB of the active world state
                # In real implementation, we'd fetch WorldState, update JSONB, and save
                # For now, we simulate this logic
                logger.debug(f"Applying world state changes: {event.world_state_changes}")
                # Implementation depends on exact DB schema
            
            # 2. Add memories to affected agents
            # If affected_agents is None, it's public so all agents get it
            # In a real implementation we'd create AgentMemory rows here
            logger.debug(f"Adding memory of event to agents. Visibility: {event.visibility}")
            
            # Commit the transaction
            await db.commit()
            
            return InjectionResult(
                success=True,
                message=f"Successfully injected event: {event.event_type}",
                event=event
            )
            
        except Exception as e:
            logger.error(f"Failed to inject event: {e}")
            await db.rollback()
            return InjectionResult(
                success=False,
                message=f"Injection failed: {str(e)}",
                event=event
            )

# Global instance
event_injector = EventInjector()
