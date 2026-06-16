"""
Agent Repository

Data access layer for agents and agent memories.
"""

from datetime import datetime
from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.agent_models import Agent, AgentMemory


class AgentRepository:
    """Data access for agents"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_agent(
        self,
        project_id: UUID,
        name: str,
        agent_type: str,
        role: str,
        personality: dict,
        mutable_psychology: Optional[dict] = None,
        entity_id: Optional[UUID] = None,
        current_state: Optional[dict] = None,
        resources: Optional[dict] = None,
    ) -> Agent:
        """Create a new agent"""
        logger.info(f"Creating agent: {name} ({agent_type})")
        
        agent = Agent(
            project_id=project_id,
            entity_id=entity_id,
            name=name,
            agent_type=agent_type,
            role=role,
            personality=personality,
            mutable_psychology=mutable_psychology or {},
            current_state=current_state or {},
            resources=resources or {},
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.debug(f"Agent created: {agent.id}")
        return agent
    
    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID"""
        result = await self.session.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()
    
    async def list_agents(
        self,
        project_id: Optional[UUID] = None,
        entity_id: Optional[UUID] = None,
        agent_type: Optional[str] = None,
    ) -> List[Agent]:
        """List agents with filters"""
        query = select(Agent)
        
        if project_id:
            query = query.where(Agent.project_id == project_id)
        if entity_id:
            query = query.where(Agent.entity_id == entity_id)
        if agent_type:
            query = query.where(Agent.agent_type == agent_type)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_agent(
        self,
        agent_id: UUID,
        name: Optional[str] = None,
        role: Optional[str] = None,
        personality: Optional[dict] = None,
        mutable_psychology: Optional[dict] = None,
        current_state: Optional[dict] = None,
        resources: Optional[dict] = None,
    ) -> Optional[Agent]:
        """Update agent"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None
        
        if name is not None:
            agent.name = name
        if role is not None:
            agent.role = role
        if personality is not None:
            agent.personality = personality
        if mutable_psychology is not None:
            agent.mutable_psychology = mutable_psychology
        if current_state is not None:
            agent.current_state = current_state
        if resources is not None:
            agent.resources = resources
        
        agent.last_active = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.debug(f"Agent updated: {agent_id}")
        return agent
    
    async def update_agent_state(
        self,
        agent_id: UUID,
        state_updates: dict,
    ) -> Optional[Agent]:
        """Update agent's current state (merge with existing)"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return None
        
        # Merge state updates
        agent.current_state.update(state_updates)
        agent.last_active = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(agent)
        
        logger.debug(f"Agent state updated: {agent_id}")
        return agent
    
    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete agent"""
        agent = await self.get_agent(agent_id)
        if not agent:
            return False
        
        await self.session.delete(agent)
        await self.session.commit()
        
        logger.info(f"Agent deleted: {agent_id}")
        return True
    
    # Memory methods
    
    async def create_memory(
        self,
        agent_id: UUID,
        memory_type: str,
        content: str,
        importance: float,
        emotional_valence: float = 0.0,
        related_agent_ids: Optional[List[UUID]] = None,
        related_entity_ids: Optional[List[UUID]] = None,
        world_state_snapshot: Optional[dict] = None,
        occurred_at: Optional[datetime] = None,
    ) -> AgentMemory:
        """Create a memory"""
        memory = AgentMemory(
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            related_agent_ids=related_agent_ids or [],
            related_entity_ids=related_entity_ids or [],
            world_state_snapshot=world_state_snapshot or {},
            occurred_at=occurred_at or datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        self.session.add(memory)
        await self.session.commit()
        await self.session.refresh(memory)
        
        return memory
    
    async def get_memory(self, memory_id: UUID) -> Optional[AgentMemory]:
        """Get memory by ID"""
        result = await self.session.execute(
            select(AgentMemory).where(AgentMemory.id == memory_id)
        )
        return result.scalar_one_or_none()
    
    async def list_memories(
        self,
        agent_id: UUID,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentMemory]:
        """List memories for an agent"""
        query = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
        
        if memory_type:
            query = query.where(AgentMemory.memory_type == memory_type)
        
        query = query.order_by(AgentMemory.occurred_at.desc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete memory"""
        memory = await self.get_memory(memory_id)
        if not memory:
            return False
        
        await self.session.delete(memory)
        await self.session.commit()
        
        return True
