"""
Agent API Endpoints

Manages agents and their memories.
"""

from datetime import datetime
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.core.database import get_db
from backend.repositories.agent_repository import AgentRepository
from backend.repositories.project_repository import ProjectRepository
from backend.repositories.entity_repository import EntityRepository
from backend.models.agent_models import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    MemoryCreate,
    MemoryResponse,
    MemoryRecallRequest,
    ContextBuildRequest,
    get_default_personality,
)
from backend.agents.agent_memory import AgentMemoryManager


router = APIRouter()


# ============================================================================
# Agent Management
# ============================================================================

@router.post("/projects/{project_id}/agents", response_model=AgentResponse)
async def create_agent(
    project_id: UUID,
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new agent.
    
    Agents are autonomous decision-makers that can be:
    - Linked to an entity (CEO of a company, leader of a nation)
    - Independent (pure AI agent, autonomous system)
    """
    logger.info(f"Creating agent in project {project_id}: {agent_data.name}")
    
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify entity exists if provided
    if agent_data.entity_id:
        entity_repo = EntityRepository(db)
        entity = await entity_repo.get_entity(agent_data.entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        if entity.project_id != project_id:
            raise HTTPException(status_code=400, detail="Entity does not belong to this project")
    
    # Use default personality if not provided
    personality = agent_data.personality.model_dump()
    if not any(v != 0.5 for v in personality.values()):
        # All values are default, use agent type default
        default_personality = get_default_personality(agent_data.agent_type.value)
        personality = default_personality.model_dump()
    
    # Create agent
    agent_repo = AgentRepository(db)
    agent = await agent_repo.create_agent(
        project_id=project_id,
        name=agent_data.name,
        agent_type=agent_data.agent_type.value,
        role=agent_data.role,
        personality=personality,
        mutable_psychology=agent_data.mutable_psychology,
        entity_id=agent_data.entity_id,
        current_state=agent_data.current_state,
        resources=agent_data.resources,
    )
    
    logger.info(f"Agent created: {agent.id}")
    return agent


@router.get("/projects/{project_id}/agents", response_model=List[AgentResponse])
async def list_agents(
    project_id: UUID,
    entity_id: Optional[UUID] = Query(None),
    agent_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all agents in a project"""
    logger.info(f"Listing agents for project {project_id}")
    
    agent_repo = AgentRepository(db)
    agents = await agent_repo.list_agents(
        project_id=project_id,
        entity_id=entity_id,
        agent_type=agent_type,
    )
    
    logger.info(f"Found {len(agents)} agents")
    return agents


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get agent by ID"""
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update agent"""
    logger.info(f"Updating agent {agent_id}")
    
    agent_repo = AgentRepository(db)
    
    # Convert personality to dict if provided
    personality_dict = agent_data.personality.model_dump() if agent_data.personality else None
    
    agent = await agent_repo.update_agent(
        agent_id=agent_id,
        name=agent_data.name,
        role=agent_data.role,
        personality=personality_dict,
        mutable_psychology=agent_data.mutable_psychology,
        current_state=agent_data.current_state,
        resources=agent_data.resources,
    )
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    logger.info(f"Agent updated: {agent_id}")
    return agent


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete agent"""
    logger.info(f"Deleting agent {agent_id}")
    
    agent_repo = AgentRepository(db)
    success = await agent_repo.delete_agent(agent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted", "agent_id": str(agent_id)}


# ============================================================================
# Agent Memory
# ============================================================================

@router.post("/agents/{agent_id}/memories", response_model=MemoryResponse)
async def create_memory(
    agent_id: UUID,
    memory_data: MemoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a memory for an agent.
    
    Memories are stored in both:
    - Database (structured data)
    - ChromaDB (semantic search)
    """
    logger.info(f"Creating memory for agent {agent_id}: {memory_data.memory_type}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create memory using memory manager (stores in both DB and ChromaDB)
    memory_manager = AgentMemoryManager(agent_id)
    memory = await memory_manager.remember(
        db=db,
        memory_type=memory_data.memory_type.value,
        content=memory_data.content,
        importance=memory_data.importance,
        emotional_valence=memory_data.emotional_valence,
        related_agents=memory_data.related_agent_ids,
        related_entities=memory_data.related_entity_ids,
        world_state=memory_data.world_state_snapshot,
        occurred_at=memory_data.occurred_at,
    )
    
    logger.info(f"Memory created: {memory.id}")
    return memory


@router.get("/agents/{agent_id}/memories", response_model=List[MemoryResponse])
async def list_memories(
    agent_id: UUID,
    memory_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List memories for an agent"""
    logger.info(f"Listing memories for agent {agent_id}")
    
    agent_repo = AgentRepository(db)
    memories = await agent_repo.list_memories(
        agent_id=agent_id,
        memory_type=memory_type,
        limit=limit,
    )
    
    logger.info(f"Found {len(memories)} memories")
    return memories


@router.get("/agents/{agent_id}/memories/recent", response_model=List[MemoryResponse])
async def get_recent_memories(
    agent_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get recent memories (short-term memory)"""
    logger.info(f"Getting recent memories for agent {agent_id}")
    
    memory_manager = AgentMemoryManager(agent_id)
    memories = await memory_manager.recall_recent(db, limit=limit)
    
    return memories


@router.get("/agents/{agent_id}/memories/important", response_model=List[MemoryResponse])
async def get_important_memories(
    agent_id: UUID,
    threshold: float = Query(0.7, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get important memories (long-term memory)"""
    logger.info(f"Getting important memories for agent {agent_id}")
    
    memory_manager = AgentMemoryManager(agent_id)
    memories = await memory_manager.recall_important(db, threshold=threshold, limit=limit)
    
    return memories


@router.post("/agents/{agent_id}/memories/recall")
async def recall_similar_memories(
    agent_id: UUID,
    recall_request: MemoryRecallRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search for similar memories"""
    logger.info(f"Recalling similar memories for agent {agent_id}: {recall_request.query}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    memory_manager = AgentMemoryManager(agent_id)
    memories = memory_manager.recall_similar(
        query=recall_request.query,
        top_k=recall_request.top_k,
    )
    
    return {
        "query": recall_request.query,
        "results": memories,
        "count": len(memories),
    }


@router.post("/agents/{agent_id}/memories/context")
async def build_decision_context(
    agent_id: UUID,
    context_request: ContextBuildRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Build decision context from memories.
    
    Combines:
    - Recent memories (what just happened)
    - Important memories (key events)
    - Similar memories (relevant past situations)
    """
    logger.info(f"Building context for agent {agent_id}: {context_request.situation}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    memory_manager = AgentMemoryManager(agent_id)
    context = await memory_manager.build_context(
        db=db,
        situation=context_request.situation,
        include_recent=context_request.include_recent,
        include_important=context_request.include_important,
        include_similar=context_request.include_similar,
    )
    
    return {
        "situation": context_request.situation,
        "context": context,
    }


@router.get("/agents/{agent_id}/memories/stats")
async def get_memory_stats(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get memory statistics for an agent"""
    logger.info(f"Getting memory stats for agent {agent_id}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    memory_manager = AgentMemoryManager(agent_id)
    stats = await memory_manager.get_memory_stats(db)
    
    return stats


# ============================================================================
# Goals Management
# ============================================================================

from backend.models.goal_models import (
    GoalCreate,
    GoalUpdate,
    GoalProgressUpdate,
    GoalResponse,
    GoalContextRequest,
)
from backend.agents.goal_system import GoalManager


@router.post("/agents/{agent_id}/goals", response_model=GoalResponse)
async def create_goal(
    agent_id: UUID,
    goal_data: GoalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new goal for an agent"""
    logger.info(f"Creating goal for agent {agent_id}: {goal_data.description}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create goal
    goal_manager = GoalManager(agent_id)
    goal = await goal_manager.add_goal(
        db=db,
        description=goal_data.description,
        goal_type=goal_data.goal_type.value,
        priority=goal_data.priority,
        deadline=goal_data.deadline,
        parent_goal_id=goal_data.parent_goal_id,
    )
    
    logger.info(f"Goal created: {goal.id}")
    return goal


@router.get("/agents/{agent_id}/goals", response_model=List[GoalResponse])
async def list_goals(
    agent_id: UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List goals for an agent"""
    logger.info(f"Listing goals for agent {agent_id}")
    
    goal_manager = GoalManager(agent_id)
    
    if status:
        goals = await goal_manager.get_all_goals(db, status=status)
    else:
        goals = await goal_manager.get_all_goals(db)
    
    logger.info(f"Found {len(goals)} goals")
    return goals


@router.get("/agents/{agent_id}/goals/active", response_model=List[GoalResponse])
async def get_active_goals(
    agent_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get active goals sorted by priority"""
    logger.info(f"Getting active goals for agent {agent_id}")
    
    goal_manager = GoalManager(agent_id)
    goals = await goal_manager.get_active_goals(db, limit=limit)
    
    return goals


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a goal"""
    logger.info(f"Updating goal {goal_id}")
    
    # Get goal to find agent_id
    from backend.models.goal_models import Goal
    from sqlalchemy import select
    
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal_manager = GoalManager(goal.agent_id)
    updated_goal = await goal_manager.update_goal(
        db=db,
        goal_id=goal_id,
        description=goal_data.description,
        goal_type=goal_data.goal_type.value if goal_data.goal_type else None,
        priority=goal_data.priority,
        status=goal_data.status.value if goal_data.status else None,
        deadline=goal_data.deadline,
    )
    
    if not updated_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    logger.info(f"Goal updated: {goal_id}")
    return updated_goal


@router.post("/goals/{goal_id}/progress", response_model=GoalResponse)
async def update_goal_progress(
    goal_id: UUID,
    progress_data: GoalProgressUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update goal progress"""
    logger.info(f"Updating progress for goal {goal_id}: {progress_data.progress}")
    
    # Get goal to find agent_id
    from backend.models.goal_models import Goal
    from sqlalchemy import select
    
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal_manager = GoalManager(goal.agent_id)
    updated_goal = await goal_manager.update_progress(
        db=db,
        goal_id=goal_id,
        progress=progress_data.progress,
    )
    
    if not updated_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return updated_goal


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a goal"""
    logger.info(f"Deleting goal {goal_id}")
    
    # Get goal to find agent_id
    from backend.models.goal_models import Goal
    from sqlalchemy import select
    
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    goal_manager = GoalManager(goal.agent_id)
    success = await goal_manager.delete_goal(db, goal_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {"message": "Goal deleted", "goal_id": str(goal_id)}


@router.post("/agents/{agent_id}/goals/context")
async def get_goal_context(
    agent_id: UUID,
    context_request: GoalContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get goal context for decision-making"""
    logger.info(f"Building goal context for agent {agent_id}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    goal_manager = GoalManager(agent_id)
    context = await goal_manager.get_goal_context(db, limit=context_request.limit)
    
    return {"context": context}


@router.get("/agents/{agent_id}/goals/stats")
async def get_goal_stats(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get goal statistics for an agent"""
    logger.info(f"Getting goal stats for agent {agent_id}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    goal_manager = GoalManager(agent_id)
    stats = await goal_manager.get_goal_stats(db)
    
    return stats


# ============================================================================
# Relationships Management
# ============================================================================

from backend.models.relationship_models import (
    RelationshipCreate,
    RelationshipUpdate,
    InteractionCreate,
    RelationshipResponse,
    InteractionResponse,
    RelationshipContextRequest,
)
from backend.agents.relationship_system import RelationshipManager


@router.post("/agents/{agent_id}/relationships", response_model=RelationshipResponse)
async def create_relationship(
    agent_id: UUID,
    relationship_data: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a relationship between agents"""
    logger.info(f"Creating relationship between {agent_id} and {relationship_data.other_agent_id}")
    
    # Verify both agents exist
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    other_agent = await agent_repo.get_agent(relationship_data.other_agent_id)
    if not other_agent:
        raise HTTPException(status_code=404, detail="Other agent not found")
    
    if agent.project_id != other_agent.project_id:
        raise HTTPException(status_code=400, detail="Agents must be in the same project")
    
    # Create relationship
    rel_manager = RelationshipManager(agent_id)
    relationship = await rel_manager.create_or_update_relationship(
        db=db,
        project_id=agent.project_id,
        other_agent_id=relationship_data.other_agent_id,
        relationship_type=relationship_data.relationship_type.value,
        strength=relationship_data.strength,
        trust=relationship_data.trust,
        influence=relationship_data.influence,
    )
    
    logger.info(f"Relationship created: {relationship.id}")
    return relationship


@router.get("/agents/{agent_id}/relationships", response_model=List[RelationshipResponse])
async def list_relationships(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all relationships for an agent"""
    logger.info(f"Listing relationships for agent {agent_id}")
    
    rel_manager = RelationshipManager(agent_id)
    relationships = await rel_manager.get_all_relationships(db)
    
    logger.info(f"Found {len(relationships)} relationships")
    return relationships


@router.get("/relationships/{relationship_id}", response_model=RelationshipResponse)
async def get_relationship(
    relationship_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get relationship by ID"""
    from backend.models.relationship_models import AgentRelationship
    from sqlalchemy import select
    
    result = await db.execute(
        select(AgentRelationship).where(AgentRelationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return relationship


@router.put("/relationships/{relationship_id}", response_model=RelationshipResponse)
async def update_relationship(
    relationship_id: UUID,
    relationship_data: RelationshipUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a relationship"""
    logger.info(f"Updating relationship {relationship_id}")
    
    from backend.models.relationship_models import AgentRelationship
    from sqlalchemy import select
    
    result = await db.execute(
        select(AgentRelationship).where(AgentRelationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    # Update fields
    if relationship_data.relationship_type is not None:
        relationship.relationship_type = relationship_data.relationship_type.value
    if relationship_data.strength is not None:
        relationship.strength = relationship_data.strength
    if relationship_data.trust is not None:
        relationship.trust = relationship_data.trust
    if relationship_data.influence is not None:
        relationship.influence = relationship_data.influence
    
    relationship.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(relationship)
    
    logger.info(f"Relationship updated: {relationship_id}")
    return relationship


@router.post("/relationships/{relationship_id}/interact", response_model=InteractionResponse)
async def record_interaction(
    relationship_id: UUID,
    interaction_data: InteractionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Record an interaction between agents"""
    logger.info(f"Recording interaction for relationship {relationship_id}")
    
    from backend.models.relationship_models import AgentRelationship
    from sqlalchemy import select
    
    result = await db.execute(
        select(AgentRelationship).where(AgentRelationship.id == relationship_id)
    )
    relationship = result.scalar_one_or_none()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    # Record interaction
    rel_manager = RelationshipManager(relationship.agent_a_id)
    interaction, updated_relationship = await rel_manager.record_interaction(
        db=db,
        project_id=relationship.project_id,
        other_agent_id=relationship.agent_b_id,
        interaction_type=interaction_data.interaction_type.value,
        description=interaction_data.description,
        outcome=interaction_data.outcome.value,
        trust_change=interaction_data.trust_change,
        strength_change=interaction_data.strength_change,
    )
    
    logger.info(f"Interaction recorded: {interaction.id}")
    return interaction


@router.get("/agents/{agent_id}/allies")
async def get_allies(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get list of allied agents"""
    logger.info(f"Getting allies for agent {agent_id}")
    
    rel_manager = RelationshipManager(agent_id)
    allies = await rel_manager.get_allies(db)
    
    return {"agent_id": str(agent_id), "allies": [str(a) for a in allies], "count": len(allies)}


@router.get("/agents/{agent_id}/enemies")
async def get_enemies(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get list of enemy agents"""
    logger.info(f"Getting enemies for agent {agent_id}")
    
    rel_manager = RelationshipManager(agent_id)
    enemies = await rel_manager.get_enemies(db)
    
    return {"agent_id": str(agent_id), "enemies": [str(e) for e in enemies], "count": len(enemies)}


@router.post("/agents/{agent_id}/relationships/context")
async def get_relationship_context(
    agent_id: UUID,
    context_request: RelationshipContextRequest,
    db: AsyncSession = Depends(get_db),
):
    """Get relationship context for decision-making"""
    logger.info(f"Building relationship context for agent {agent_id}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    rel_manager = RelationshipManager(agent_id)
    context = await rel_manager.get_relationship_context(db, limit=context_request.limit)
    
    return {"context": context}


@router.get("/agents/{agent_id}/relationships/stats")
async def get_relationship_stats(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get relationship statistics for an agent"""
    logger.info(f"Getting relationship stats for agent {agent_id}")
    
    # Verify agent exists
    agent_repo = AgentRepository(db)
    agent = await agent_repo.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    rel_manager = RelationshipManager(agent_id)
    stats = await rel_manager.get_relationship_stats(db)
    
    return stats
