"""
World State Manager - Manages world state and evolution
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.world_models import WorldState, WorldEvent


class WorldManager:
    """Manages world state for projects"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_world_state(
        self,
        project_id: UUID,
        initial_state: Optional[Dict[str, Any]] = None,
    ) -> WorldState:
        """Create world state for a project"""
        world_state = WorldState(
            project_id=project_id,
            state=initial_state or {},
        )
        self.session.add(world_state)
        await self.session.commit()
        await self.session.refresh(world_state)
        return world_state
    
    async def get_world_state(self, project_id: UUID) -> Optional[WorldState]:
        """Get world state for a project"""
        result = await self.session.execute(
            select(WorldState).where(WorldState.project_id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def update_world_state(
        self,
        project_id: UUID,
        state_updates: Dict[str, Any],
    ) -> Optional[WorldState]:
        """Update world state (merges with existing state)"""
        world_state = await self.get_world_state(project_id)
        if not world_state:
            return None
        
        # Merge updates into existing state
        current_state = world_state.state or {}
        current_state.update(state_updates)
        world_state.state = current_state
        world_state.last_updated = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(world_state)
        return world_state
    
    async def get_current_state(self, project_id: UUID) -> Dict[str, Any]:
        """Get current world state as dict"""
        world_state = await self.get_world_state(project_id)
        return world_state.state if world_state else {}
    
    async def record_event(
        self,
        project_id: UUID,
        event_type: str,
        description: str,
        impact_score: Optional[float] = None,
        affected_entity_ids: Optional[List[UUID]] = None,
        occurred_at: Optional[datetime] = None,
    ) -> WorldEvent:
        """Record a world event"""
        # Get or create world state
        world_state = await self.get_world_state(project_id)
        if not world_state:
            world_state = await self.create_world_state(project_id)
        
        # Create event
        event = WorldEvent(
            world_state_id=world_state.id,
            event_type=event_type,
            description=description,
            impact_score=impact_score,
            affected_entity_ids=affected_entity_ids,
            occurred_at=occurred_at or datetime.utcnow(),
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event
    
    async def get_events(
        self,
        project_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
    ) -> List[WorldEvent]:
        """Get world events with optional filters"""
        world_state = await self.get_world_state(project_id)
        if not world_state:
            return []
        
        query = select(WorldEvent).where(WorldEvent.world_state_id == world_state.id)
        
        if start_date:
            query = query.where(WorldEvent.occurred_at >= start_date)
        if end_date:
            query = query.where(WorldEvent.occurred_at <= end_date)
        if event_type:
            query = query.where(WorldEvent.event_type == event_type)
        
        query = query.order_by(WorldEvent.occurred_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_world_snapshot(self, project_id: UUID) -> Dict[str, Any]:
        """Get complete world snapshot including state and recent events"""
        world_state = await self.get_world_state(project_id)
        if not world_state:
            return {
                "state": {},
                "recent_events": [],
                "last_updated": None,
            }
        
        # Get recent events (last 10)
        recent_events = await self.get_events(project_id)
        recent_events = recent_events[:10]
        
        return {
            "state": world_state.state,
            "recent_events": [e.to_dict() for e in recent_events],
            "last_updated": world_state.last_updated.isoformat(),
        }
