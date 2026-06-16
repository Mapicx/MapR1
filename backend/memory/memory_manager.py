"""
Memory Manager - High-level interface for storing and retrieving memories
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from loguru import logger

from backend.memory.vector_store import get_vector_store


class MemoryManager:
    """Manages semantic memory for worlds"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
    
    def store_scenario(
        self,
        project_id: UUID,
        scenario_id: UUID,
        title: str,
        description: str,
        category: str,
        timeline_events: List[Dict[str, Any]],
    ) -> str:
        """
        Store a scenario in memory
        
        Returns:
            Memory ID
        """
        # Create rich content for embedding
        events_text = "\n".join([
            f"Year {e['year']}: {e['description']}" 
            for e in timeline_events
        ])
        
        content = f"""
Scenario: {title}
Category: {category}
Description: {description}

Timeline:
{events_text}
        """.strip()
        
        memory_id = f"scenario_{scenario_id}"
        
        metadata = {
            "project_id": str(project_id),
            "scenario_id": str(scenario_id),
            "type": "scenario",
            "category": category,
            "title": title,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.vector_store.add_memory(memory_id, content, metadata)
        logger.info(f"Stored scenario in memory: {title}")
        
        return memory_id
    
    def store_event(
        self,
        project_id: UUID,
        event_id: UUID,
        event_type: str,
        description: str,
        impact_score: Optional[float] = None,
    ) -> str:
        """
        Store a world event in memory
        
        Returns:
            Memory ID
        """
        content = f"""
Event Type: {event_type}
Description: {description}
Impact: {impact_score if impact_score else 'Unknown'}
        """.strip()
        
        memory_id = f"event_{event_id}"
        
        metadata = {
            "project_id": str(project_id),
            "event_id": str(event_id),
            "type": "event",
            "event_type": event_type,
            "impact_score": impact_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.vector_store.add_memory(memory_id, content, metadata)
        logger.debug(f"Stored event in memory: {event_type}")
        
        return memory_id
    
    def store_entity(
        self,
        project_id: UUID,
        entity_id: UUID,
        entity_type: str,
        name: str,
        description: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store an entity in memory
        
        Returns:
            Memory ID
        """
        attrs_text = ""
        if attributes:
            attrs_text = "\n".join([f"{k}: {v}" for k, v in attributes.items()])
        
        content = f"""
Entity: {name}
Type: {entity_type}
Description: {description or 'No description'}

Attributes:
{attrs_text}
        """.strip()
        
        memory_id = f"entity_{entity_id}"
        
        metadata = {
            "project_id": str(project_id),
            "entity_id": str(entity_id),
            "type": "entity",
            "entity_type": entity_type,
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.vector_store.add_memory(memory_id, content, metadata)
        logger.debug(f"Stored entity in memory: {name}")
        
        return memory_id
    
    def search_similar_scenarios(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find scenarios similar to the query
        
        Args:
            query: Search query
            project_id: Filter by project
            top_k: Number of results
        
        Returns:
            List of similar scenarios with metadata
        """
        return self.vector_store.search(
            query=query,
            project_id=str(project_id) if project_id else None,
            n_results=top_k,
            filters={"type": "scenario"},
        )
    
    def search_similar_events(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find events similar to the query"""
        return self.vector_store.search(
            query=query,
            project_id=str(project_id) if project_id else None,
            n_results=top_k,
            filters={"type": "event"},
        )
    
    def search_all(
        self,
        query: str,
        project_id: Optional[UUID] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search across all memory types"""
        return self.vector_store.search(
            query=query,
            project_id=str(project_id) if project_id else None,
            n_results=top_k,
        )
    
    def get_world_history(
        self,
        project_id: UUID,
        limit: Optional[int] = 50,
    ) -> List[Dict[str, Any]]:
        """Get all memories for a world/project"""
        return self.vector_store.get_project_memories(
            project_id=str(project_id),
            limit=limit,
        )
    
    def get_memory_stats(self, project_id: Optional[UUID] = None) -> Dict[str, int]:
        """Get memory statistics"""
        if project_id:
            memories = self.vector_store.get_project_memories(str(project_id))
            
            stats = {
                "total": len(memories),
                "scenarios": sum(1 for m in memories if m["metadata"].get("type") == "scenario"),
                "events": sum(1 for m in memories if m["metadata"].get("type") == "event"),
                "entities": sum(1 for m in memories if m["metadata"].get("type") == "entity"),
            }
        else:
            total = self.vector_store.count_memories()
            stats = {"total": total}
        
        return stats
    
    def delete_project_memories(self, project_id: UUID) -> int:
        """Delete all memories for a project"""
        return self.vector_store.delete_project_memories(str(project_id))


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
