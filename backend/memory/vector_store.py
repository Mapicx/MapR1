"""
Vector Store using ChromaDB for semantic memory
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from uuid import UUID
from loguru import logger

from backend.core.config import settings


class VectorStore:
    """ChromaDB vector store for semantic memory"""
    
    def __init__(self):
        """Initialize ChromaDB client"""
        # Use persistent storage
        self.client = chromadb.PersistentClient(
            path="./embeddings",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="mapr1_memories",
            metadata={"description": "MapR1 world memories and events"}
        )
        
        logger.info("Vector store initialized with ChromaDB")
    
    def add_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Add a memory to the vector store
        
        Args:
            memory_id: Unique ID for the memory
            content: Text content to embed
            metadata: Additional metadata (project_id, timestamp, etc.)
        """
        try:
            self.collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[metadata],
            )
            logger.debug(f"Added memory: {memory_id}")
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise
    
    def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories
        
        Args:
            query: Search query text
            project_id: Filter by project ID
            n_results: Number of results to return
            filters: Additional metadata filters
        
        Returns:
            List of matching memories with metadata
        """
        try:
            # Build where clause with proper ChromaDB syntax
            where = None
            
            if project_id and filters:
                # Multiple conditions - use $and
                where = {
                    "$and": [
                        {"project_id": project_id},
                        filters
                    ]
                }
            elif project_id:
                where = {"project_id": project_id}
            elif filters:
                where = filters
            
            # Search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
            )
            
            # Format results
            memories = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    memories.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                    })
            
            logger.debug(f"Found {len(memories)} memories for query: {query[:50]}...")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific memory by ID"""
        try:
            result = self.collection.get(ids=[memory_id])
            
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return None
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory"""
        try:
            self.collection.delete(ids=[memory_id])
            logger.debug(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False
    
    def delete_project_memories(self, project_id: str) -> int:
        """Delete all memories for a project"""
        try:
            # Get all memories for project
            results = self.collection.get(
                where={"project_id": project_id}
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                count = len(results["ids"])
                logger.info(f"Deleted {count} memories for project {project_id}")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete project memories: {e}")
            return 0
    
    def get_project_memories(
        self,
        project_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get all memories for a project"""
        try:
            results = self.collection.get(
                where={"project_id": project_id},
                limit=limit,
            )
            
            memories = []
            if results["ids"]:
                for i in range(len(results["ids"])):
                    memories.append({
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i],
                    })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get project memories: {e}")
            return []
    
    def count_memories(self, project_id: Optional[str] = None) -> int:
        """Count memories, optionally filtered by project"""
        try:
            if project_id:
                results = self.collection.get(where={"project_id": project_id})
                return len(results["ids"]) if results["ids"] else 0
            else:
                return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count memories: {e}")
            return 0


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
