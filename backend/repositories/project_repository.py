"""
MapR1 — Project Repository
Database operations for projects/worlds.
"""

import uuid
from typing import List, Optional

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.db_models import DBScenario, Project


class ProjectRepository:
    """Repository for project database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, name: str, description: Optional[str] = None) -> Project:
        """
        Create a new project

        Args:
            name: Project name
            description: Optional description

        Returns:
            Created Project
        """
        try:
            project = Project(name=name, description=description)
            self.db.add(project)
            await self.db.flush()
            logger.info(f"Created project: {name} (ID: {project.id})")
            return project
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise

    async def get_project(self, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by ID"""
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def list_projects(self, limit: int = 50, offset: int = 0) -> List[Project]:
        """
        List all projects

        Args:
            limit: Maximum number to return
            offset: Pagination offset

        Returns:
            List of projects
        """
        result = await self.db.execute(
            select(Project).order_by(desc(Project.updated_at)).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update_project(
        self, project_id: uuid.UUID, name: Optional[str] = None, description: Optional[str] = None
    ) -> Optional[Project]:
        """
        Update project details

        Args:
            project_id: Project to update
            name: New name (optional)
            description: New description (optional)

        Returns:
            Updated project or None
        """
        project = await self.get_project(project_id)
        if project:
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            project.updated_at = func.now()
            await self.db.flush()
            logger.info(f"Updated project {project_id}")
        return project

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        """
        Delete a project (cascade deletes scenarios)

        Args:
            project_id: Project to delete

        Returns:
            True if deleted, False if not found
        """
        project = await self.get_project(project_id)
        if project:
            await self.db.delete(project)
            await self.db.flush()
            logger.info(f"Deleted project {project_id}")
            return True
        return False

    async def get_project_scenarios(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> List[DBScenario]:
        """
        Get all scenarios for a project

        Args:
            project_id: Project ID
            limit: Maximum scenarios to return

        Returns:
            List of scenarios
        """
        result = await self.db.execute(
            select(DBScenario)
            .where(DBScenario.project_id == project_id)
            .options(selectinload(DBScenario.timeline_events))
            .order_by(desc(DBScenario.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_project_stats(self, project_id: uuid.UUID) -> dict:
        """
        Get statistics for a project

        Args:
            project_id: Project ID

        Returns:
            Dictionary with stats
        """
        from backend.models.agent_models import Agent
        from backend.models.entity_models import Entity
        
        # Count scenarios
        scenario_count = await self.db.scalar(
            select(func.count(DBScenario.id)).where(DBScenario.project_id == project_id)
        )

        # Count saved scenarios
        saved_count = await self.db.scalar(
            select(func.count(DBScenario.id)).where(
                DBScenario.project_id == project_id, DBScenario.saved == True
            )
        )

        # Count entities
        entity_count = await self.db.scalar(
            select(func.count(Entity.id)).where(Entity.project_id == project_id)
        )

        # Count agents
        agent_count = await self.db.scalar(
            select(func.count(Agent.id)).where(Agent.project_id == project_id)
        )

        return {
            "total_scenarios": scenario_count or 0,
            "saved_scenarios": saved_count or 0,
            "unsaved_scenarios": (scenario_count or 0) - (saved_count or 0),
            "entities": entity_count or 0,
            "agents": agent_count or 0,
        }
