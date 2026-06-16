"""
Timeline Repository - Data access layer for timelines
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.timeline_models import Timeline, TimelineScenario


class TimelineRepository:
    """Repository for timeline CRUD operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_timeline(
        self,
        project_id: UUID,
        name: str,
        description: Optional[str] = None,
        parent_timeline_id: Optional[UUID] = None,
        branch_point_year: Optional[int] = None,
        branch_description: Optional[str] = None,
    ) -> Timeline:
        """Create a new timeline"""
        timeline = Timeline(
            project_id=project_id,
            name=name,
            description=description,
            parent_timeline_id=parent_timeline_id,
            branch_point_year=branch_point_year,
            branch_description=branch_description,
        )
        self.session.add(timeline)
        await self.session.commit()
        await self.session.refresh(timeline)
        return timeline
    
    async def get_timeline(self, timeline_id: UUID) -> Optional[Timeline]:
        """Get timeline by ID with scenarios"""
        result = await self.session.execute(
            select(Timeline)
            .where(Timeline.id == timeline_id)
            .options(selectinload(Timeline.scenarios))
        )
        return result.scalar_one_or_none()
    
    async def list_timelines(
        self,
        project_id: Optional[UUID] = None,
        parent_timeline_id: Optional[UUID] = None,
    ) -> List[Timeline]:
        """List timelines with optional filters"""
        query = select(Timeline).options(selectinload(Timeline.scenarios))
        
        conditions = []
        if project_id:
            conditions.append(Timeline.project_id == project_id)
        if parent_timeline_id:
            conditions.append(Timeline.parent_timeline_id == parent_timeline_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_timeline(
        self,
        timeline_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Timeline]:
        """Update timeline"""
        timeline = await self.get_timeline(timeline_id)
        if not timeline:
            return None
        
        if name is not None:
            timeline.name = name
        if description is not None:
            timeline.description = description
        
        await self.session.commit()
        await self.session.refresh(timeline)
        return timeline
    
    async def delete_timeline(self, timeline_id: UUID) -> bool:
        """Delete timeline"""
        timeline = await self.get_timeline(timeline_id)
        if not timeline:
            return False
        
        await self.session.delete(timeline)
        await self.session.commit()
        return True
    
    async def add_scenario_to_timeline(
        self,
        timeline_id: UUID,
        scenario_id: UUID,
        sequence_order: int = 0,
    ) -> TimelineScenario:
        """Add a scenario to a timeline"""
        timeline_scenario = TimelineScenario(
            timeline_id=timeline_id,
            scenario_id=scenario_id,
            sequence_order=sequence_order,
        )
        self.session.add(timeline_scenario)
        await self.session.commit()
        return timeline_scenario
    
    async def remove_scenario_from_timeline(
        self,
        timeline_id: UUID,
        scenario_id: UUID,
    ) -> bool:
        """Remove a scenario from a timeline"""
        result = await self.session.execute(
            select(TimelineScenario).where(
                and_(
                    TimelineScenario.timeline_id == timeline_id,
                    TimelineScenario.scenario_id == scenario_id,
                )
            )
        )
        timeline_scenario = result.scalar_one_or_none()
        
        if not timeline_scenario:
            return False
        
        await self.session.delete(timeline_scenario)
        await self.session.commit()
        return True
    
    async def get_timeline_scenarios(self, timeline_id: UUID) -> List[UUID]:
        """Get all scenario IDs in a timeline"""
        result = await self.session.execute(
            select(TimelineScenario.scenario_id)
            .where(TimelineScenario.timeline_id == timeline_id)
            .order_by(TimelineScenario.sequence_order)
        )
        return list(result.scalars().all())
