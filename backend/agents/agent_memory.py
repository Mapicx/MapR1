"""
Agent Memory Manager

Manages agent memory storage and recall:
- Store memories in both database (structured) and ChromaDB (semantic)
- Recall recent memories (short-term memory)
- Recall important memories (long-term memory)
- Semantic search for similar memories
- Build decision context from memories
"""

from datetime import datetime
from uuid import UUID
from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.agent_models import AgentMemory, MemoryType
from backend.memory.vector_store import get_vector_store


class AgentMemoryManager:
    """Manages agent memory storage and recall"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
        self.vector_store = get_vector_store()
    
    async def remember(
        self,
        db: AsyncSession,
        memory_type: str,
        content: str,
        importance: float,
        emotional_valence: float = 0.0,
        related_agents: Optional[List[UUID]] = None,
        related_entities: Optional[List[UUID]] = None,
        world_state: Optional[dict] = None,
        occurred_at: Optional[datetime] = None,
    ) -> AgentMemory:
        """
        Store a memory in both database and vector store.
        
        Args:
            memory_type: observation, interaction, decision, emotion
            content: What happened
            importance: 0-1 (how significant)
            emotional_valence: -1 to 1 (negative to positive)
            related_agents: Other agents involved
            related_entities: Entities involved
            world_state: World state at time of memory
            occurred_at: When the memory occurred (defaults to now)
        
        Returns:
            Created AgentMemory
        """
        logger.info(f"Agent {self.agent_id} remembering: {memory_type} - {content[:50]}...")
        
        # Create memory in database
        memory = AgentMemory(
            agent_id=self.agent_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            emotional_valence=emotional_valence,
            related_agent_ids=related_agents or [],
            related_entity_ids=related_entities or [],
            world_state_snapshot=world_state or {},
            occurred_at=occurred_at or datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        
        # Store in vector store for semantic search
        try:
            self.vector_store.add_memory(
                memory_id=f"agent_memory_{memory.id}",
                content=content,
                metadata={
                    "agent_id": str(self.agent_id),
                    "memory_type": memory_type,
                    "importance": importance,
                    "emotional_valence": emotional_valence,
                    "timestamp": memory.occurred_at.isoformat(),
                    "type": "agent_memory",  # For filtering
                }
            )
            logger.debug(f"Memory stored in vector store: {memory.id}")
        except Exception as e:
            logger.error(f"Failed to store memory in vector store: {e}")
        
        return memory
    
    async def recall_recent(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> List[AgentMemory]:
        """
        Get recent memories (short-term memory).
        
        Args:
            limit: Number of memories to retrieve
        
        Returns:
            List of recent memories
        """
        logger.debug(f"Recalling {limit} recent memories for agent {self.agent_id}")
        
        result = await db.execute(
            select(AgentMemory)
            .where(AgentMemory.agent_id == self.agent_id)
            .order_by(AgentMemory.occurred_at.desc())
            .limit(limit)
        )
        memories = list(result.scalars().all())
        
        logger.info(f"Recalled {len(memories)} recent memories")
        return memories
    
    async def recall_important(
        self,
        db: AsyncSession,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[AgentMemory]:
        """
        Get important memories (long-term memory).
        
        Args:
            threshold: Minimum importance (0-1)
            limit: Number of memories to retrieve
        
        Returns:
            List of important memories
        """
        logger.debug(f"Recalling important memories (threshold={threshold}) for agent {self.agent_id}")
        
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.importance >= threshold
            )
            .order_by(AgentMemory.importance.desc())
            .limit(limit)
        )
        memories = list(result.scalars().all())
        
        logger.info(f"Recalled {len(memories)} important memories")
        return memories
    
    def recall_similar(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Semantic search for similar memories.
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of similar memories with metadata
        """
        logger.debug(f"Searching for memories similar to: {query[:50]}...")
        
        try:
            results = self.vector_store.search(
                query=query,
                n_results=top_k,
                filters={
                    "$and": [
                        {"agent_id": str(self.agent_id)},
                        {"type": "agent_memory"}
                    ]
                }
            )
            
            logger.info(f"Found {len(results)} similar memories")
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def recall_about_agent(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
        limit: int = 10,
    ) -> List[AgentMemory]:
        """
        Get memories involving another agent.
        
        Args:
            other_agent_id: ID of the other agent
            limit: Number of memories to retrieve
        
        Returns:
            List of memories involving the other agent
        """
        logger.debug(f"Recalling memories about agent {other_agent_id}")
        
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.related_agent_ids.contains([other_agent_id])
            )
            .order_by(AgentMemory.occurred_at.desc())
            .limit(limit)
        )
        memories = list(result.scalars().all())
        
        logger.info(f"Recalled {len(memories)} memories about agent {other_agent_id}")
        return memories
    
    async def recall_about_entity(
        self,
        db: AsyncSession,
        entity_id: UUID,
        limit: int = 10,
    ) -> List[AgentMemory]:
        """
        Get memories involving an entity.
        
        Args:
            entity_id: ID of the entity
            limit: Number of memories to retrieve
        
        Returns:
            List of memories involving the entity
        """
        logger.debug(f"Recalling memories about entity {entity_id}")
        
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.related_entity_ids.contains([entity_id])
            )
            .order_by(AgentMemory.occurred_at.desc())
            .limit(limit)
        )
        memories = list(result.scalars().all())
        
        logger.info(f"Recalled {len(memories)} memories about entity {entity_id}")
        return memories
    
    async def build_context(
        self,
        db: AsyncSession,
        situation: str,
        include_recent: int = 5,
        include_important: int = 5,
        include_similar: int = 5,
    ) -> str:
        """
        Build context for decision-making.
        
        Combines:
        - Recent memories (what just happened)
        - Important memories (key events)
        - Relevant memories (similar situations)
        
        Args:
            situation: Current situation description
            include_recent: Number of recent memories
            include_important: Number of important memories
            include_similar: Number of similar memories
        
        Returns:
            Context string for LLM
        """
        logger.info(f"Building decision context for situation: {situation[:50]}...")
        
        context_parts = []
        
        # Get recent memories
        recent = await self.recall_recent(db, limit=include_recent)
        if recent:
            context_parts.append("=== RECENT EVENTS ===")
            for m in recent:
                valence = "😊" if m.emotional_valence > 0.3 else "😢" if m.emotional_valence < -0.3 else "😐"
                context_parts.append(f"{valence} [{m.memory_type}] {m.content}")
        
        # Get important memories
        important = await self.recall_important(db, threshold=0.8, limit=include_important)
        if important:
            context_parts.append("\n=== IMPORTANT MEMORIES ===")
            for m in important:
                valence = "😊" if m.emotional_valence > 0.3 else "😢" if m.emotional_valence < -0.3 else "😐"
                context_parts.append(f"{valence} [{m.memory_type}] {m.content} (importance: {m.importance:.1f})")
        
        # Get semantically similar memories
        similar = self.recall_similar(situation, top_k=include_similar)
        if similar:
            context_parts.append("\n=== SIMILAR PAST SITUATIONS ===")
            for m in similar:
                context_parts.append(f"- {m['content']}")
        
        context = "\n".join(context_parts)
        logger.debug(f"Built context with {len(context)} characters")
        
        return context if context else "No relevant memories found."
    
    async def get_memory_stats(self, db: AsyncSession) -> Dict:
        """
        Get statistics about agent's memories.
        
        Returns:
            Dictionary with memory statistics
        """
        result = await db.execute(
            select(AgentMemory)
            .where(AgentMemory.agent_id == self.agent_id)
        )
        memories = list(result.scalars().all())
        
        if not memories:
            return {
                "total": 0,
                "by_type": {},
                "avg_importance": 0.0,
                "avg_emotional_valence": 0.0,
            }
        
        # Count by type
        by_type = {}
        for m in memories:
            by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
        
        # Calculate averages
        avg_importance = sum(m.importance for m in memories) / len(memories)
        avg_valence = sum(m.emotional_valence for m in memories) / len(memories)
        
        return {
            "total": len(memories),
            "by_type": by_type,
            "avg_importance": round(avg_importance, 2),
            "avg_emotional_valence": round(avg_valence, 2),
        }
