"""
MapR1 — Scenario Repository
Database operations for scenarios and timeline events.
"""

import uuid
from typing import List, Optional

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.db_models import DBScenario, DBTimelineEvent, Project
from backend.models.scenario import Scenario, TimelineEvent


class ScenarioRepository:
    """Repository for scenario database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_scenario(
        self,
        scenario: Scenario,
        prompt: str,
        request_id: uuid.UUID,
        model_used: str,
        project_id: Optional[uuid.UUID] = None,
        saved: bool = False,
    ) -> DBScenario:
        """
        Save a scenario to the database

        Args:
            scenario: Scenario object to save
            prompt: Original user prompt
            request_id: Request ID from generation
            model_used: LLM model used
            project_id: Optional project to associate with
            saved: Whether user explicitly saved this

        Returns:
            Created DBScenario with ID
        """
        try:
            # Create scenario record
            db_scenario = DBScenario(
                id=uuid.UUID(scenario.id) if isinstance(scenario.id, str) else scenario.id,
                project_id=project_id,
                request_id=request_id,
                prompt=prompt,
                title=scenario.title,
                description=scenario.description,
                category=scenario.category.value,
                probability=scenario.probability,
                model_used=model_used,
                saved=saved,
            )

            self.db.add(db_scenario)

            # Create timeline events
            for idx, event in enumerate(scenario.timeline):
                db_event = DBTimelineEvent(
                    scenario_id=db_scenario.id,
                    year=event.year,
                    description=event.description,
                    impact=event.impact,
                    sequence_order=idx,
                )
                self.db.add(db_event)

            await self.db.flush()
            logger.info(f"Saved scenario: {db_scenario.title} (ID: {db_scenario.id})")

            return db_scenario

        except Exception as e:
            logger.error(f"Failed to save scenario: {e}")
            raise

    async def get_scenario(self, scenario_id: uuid.UUID) -> Optional[DBScenario]:
        """Get scenario by ID with timeline events"""
        result = await self.db.execute(
            select(DBScenario)
            .where(DBScenario.id == scenario_id)
            .options(selectinload(DBScenario.timeline_events))
        )
        return result.scalar_one_or_none()

    async def list_scenarios(
        self,
        project_id: Optional[uuid.UUID] = None,
        saved_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DBScenario]:
        """
        List scenarios with optional filters

        Args:
            project_id: Filter by project
            saved_only: Only return saved scenarios
            limit: Maximum number to return
            offset: Pagination offset

        Returns:
            List of scenarios
        """
        query = select(DBScenario).options(selectinload(DBScenario.timeline_events))

        if project_id:
            query = query.where(DBScenario.project_id == project_id)

        if saved_only:
            query = query.where(DBScenario.saved == True)

        query = query.order_by(desc(DBScenario.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_as_saved(self, scenario_id: uuid.UUID) -> Optional[DBScenario]:
        """Mark a scenario as saved by user"""
        scenario = await self.get_scenario(scenario_id)
        if scenario:
            scenario.saved = True
            await self.db.flush()
            logger.info(f"Marked scenario {scenario_id} as saved")
        return scenario

    async def delete_scenario(self, scenario_id: uuid.UUID) -> bool:
        """Delete a scenario (cascade deletes timeline events)"""
        scenario = await self.get_scenario(scenario_id)
        if scenario:
            await self.db.delete(scenario)
            await self.db.flush()
            logger.info(f"Deleted scenario {scenario_id}")
            return True
        return False

    async def search_scenarios(self, query: str, limit: int = 20) -> List[DBScenario]:
        """
        Search scenarios by title or description

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Matching scenarios
        """
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(DBScenario)
            .where(
                (DBScenario.title.ilike(search_pattern))
                | (DBScenario.description.ilike(search_pattern))
            )
            .options(selectinload(DBScenario.timeline_events))
            .order_by(desc(DBScenario.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
