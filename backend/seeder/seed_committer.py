"""
MapR1 — Seed Committer

Commits a generated seed to the database, creating all entities, agents, goals, etc.

IMPORTANT: This bypasses the repository layer and creates SQLAlchemy objects directly
so that we control the entire transaction ourselves (one single commit at the end).
The repositories call session.commit() internally which would break our atomic operation.
"""

from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.seeder.seed_models import CompleteSeed, CommitResponse
from backend.models.db_models import Project
from backend.models.entity_models import Entity
from backend.models.agent_models import Agent, AgentType, Personality
from backend.models.world_models import WorldState, StructuredWorldState
from backend.models.goal_models import Goal, GoalType
from backend.models.relationship_models import AgentRelationship
from backend.models.belief_models import AgentBeliefState, PublicBeliefState
from backend.agents.world_knowledge import world_knowledge_system


class SeedCommitter:
    """Commits generated seeds to the database."""
    
    async def commit(
        self,
        db: AsyncSession,
        seed: CompleteSeed,
    ) -> CommitResponse:
        """
        Commit a seed to the database, creating all entities.
        
        Args:
            db: Database session
            seed: Complete seed to commit
        
        Returns:
            CommitResponse with created entity counts
        """
        logger.info(f"Committing seed '{seed.dna.title}' to database...")
        
        try:
            # ── Step 1: Create Project ──────────────────────────────────────
            project = Project(
                id=uuid4(),
                name=seed.dna.title,
                description=seed.dna.premise,
            )
            db.add(project)
            await db.flush()
            project_id = project.id
            logger.info(f"✓ Created project: {project_id}")
            
            # Pre-seed PublicBeliefState to prevent concurrent unique violations
            public_belief = PublicBeliefState(
                project_id=project_id,
                beliefs={}
            )
            db.add(public_belief)
            
            # ── Step 2: Create World State ──────────────────────────────────
            structured_state = StructuredWorldState(
                agent_resources={},
                agent_reputation={},
                agent_power={},
                agent_exposure={},
                alliances=[],
                rivalries=[],
                public_opinion=seed.world_fabric.public_opinion,
                market_conditions=seed.world_fabric.market_conditions,
                regulatory_pressure=seed.world_fabric.regulatory_pressure,
                media_attention=seed.world_fabric.media_attention,
                recent_events=[],
                pending_proposals=[],
                metadata={
                    "suggested_steps": seed.dna.recommended_step_count,
                    # TECHNICAL DEBT: Storing CompiledTheme inside JSONB metadata.
                    # This avoids a schema migration for now, but CompiledTheme 
                    # eventually deserves its own dedicated DB table/column.
                    "theme": seed.compiled_theme,
                },
            )
            
            world_state = WorldState(
                project_id=project_id,
                state=structured_state.to_dict(),
            )
            db.add(world_state)
            await db.flush()
            logger.info(f"✓ Created world state")
            
            # ── Step 3: Create Entities ─────────────────────────────────────
            entity_map: Dict[str, UUID] = {}  # name -> id
            
            for entity_seed in seed.entities:
                entity = Entity(
                    id=uuid4(),
                    project_id=project_id,
                    type=entity_seed.type,
                    name=entity_seed.name,
                    description=entity_seed.description,
                    attributes=entity_seed.attributes or {},
                )
                db.add(entity)
                entity_map[entity_seed.name] = entity.id
            
            await db.flush()
            logger.info(f"✓ Created {len(entity_map)} entities")
            
            # ── Step 4: Create Agents ───────────────────────────────────────
            agent_map: Dict[str, UUID] = {}  # name -> id
            
            for agent_seed in seed.agents:
                agent_type = agent_seed.agent_type
                
                # Get entity_id
                entity_id = entity_map.get(agent_seed.entity_name)
                if not entity_id:
                    logger.warning(
                        f"Entity '{agent_seed.entity_name}' not found for agent '{agent_seed.name}'"
                    )
                    continue
                
                # Create personality dict from seed personality
                personality_dict = {
                    "openness": agent_seed.personality.openness,
                    "conscientiousness": agent_seed.personality.conscientiousness,
                    "extraversion": agent_seed.personality.extraversion,
                    "agreeableness": agent_seed.personality.agreeableness,
                    "neuroticism": agent_seed.personality.neuroticism,
                    "risk_tolerance": agent_seed.personality.risk_tolerance,
                    "ambition": agent_seed.personality.ambition,
                    "empathy": agent_seed.personality.empathy,
                    "rationality": agent_seed.personality.rationality,
                    "creativity": agent_seed.personality.creativity,
                    "morality": agent_seed.personality.morality,
                }
                
                # Create agent directly — bypassing AgentRepository
                agent = Agent(
                    id=uuid4(),
                    project_id=project_id,
                    entity_id=entity_id,
                    name=agent_seed.name,
                    agent_type=agent_type,
                    role=agent_seed.role,
                    personality=personality_dict,
                    current_state={"backstory": agent_seed.backstory, "secret": agent_seed.secret},
                    resources=agent_seed.initial_resources or {},
                    created_at=datetime.utcnow(),
                    last_active=datetime.utcnow(),
                )
                db.add(agent)
                
                # Pre-seed AgentBeliefState to prevent concurrent unique violation in step 1
                belief_state = AgentBeliefState(
                    agent_id=agent.id,
                    known_facts={},
                    trust_in_others={},
                    propaganda_power=0.5,
                    credibility=0.5
                )
                db.add(belief_state)
                agent_map[agent_seed.name] = agent.id
                
                # Initialize agent resources in world state
                structured_state.agent_resources[str(agent.id)] = agent_seed.initial_resources.get("funding", 0.5)
                structured_state.agent_reputation[str(agent.id)] = agent_seed.initial_reputation
                structured_state.agent_power[str(agent.id)] = agent_seed.initial_resources.get("influence", 0.5)
            
            await db.flush()
            logger.info(f"✓ Created {len(agent_map)} agents")
            
            # Update world state with agent resources
            world_state.state = structured_state.to_dict()
            
            # ── Step 5: Create Goals ────────────────────────────────────────
            goals_created = 0
            for goal_seed in seed.goals:
                agent_id = agent_map.get(goal_seed.agent_name)
                if not agent_id:
                    logger.warning(f"Agent '{goal_seed.agent_name}' not found for goal")
                    continue
                
                goal_type = goal_seed.goal_type
                
                goal = Goal(
                    id=uuid4(),
                    agent_id=agent_id,
                    description=goal_seed.description,
                    goal_type=goal_type,
                    priority=goal_seed.priority,
                    status="active",
                )
                db.add(goal)
                goals_created += 1
            
            await db.flush()
            logger.info(f"✓ Created {goals_created} goals")
            
            # ── Step 6: Create Relationships ────────────────────────────────
            relationships_created = 0
            for rel_seed in seed.relationships:
                agent_a_id = agent_map.get(rel_seed.agent_a_name)
                agent_b_id = agent_map.get(rel_seed.agent_b_name)
                
                if not agent_a_id or not agent_b_id:
                    logger.warning(
                        f"Agents not found for relationship: "
                        f"{rel_seed.agent_a_name} <-> {rel_seed.agent_b_name}"
                    )
                    continue
                
                # Create relationship directly — bypassing RelationshipManager
                relationship = AgentRelationship(
                    id=uuid4(),
                    project_id=project_id,
                    agent_a_id=agent_a_id,
                    agent_b_id=agent_b_id,
                    relationship_type=rel_seed.relationship_type,
                    trust=rel_seed.trust,
                    strength=rel_seed.strength,
                    interaction_count=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(relationship)
                relationships_created += 1
            
            await db.flush()
            logger.info(f"✓ Created {relationships_created} relationships")
            
            # ── Step 7: Seed Hidden Facts ───────────────────────────────────
            world_knowledge_system.register_scenario_facts(
                project_id=project_id,
                facts=seed.hidden_facts,
            )
            logger.info(f"✓ Seeded {len(seed.hidden_facts)} hidden facts")
            
            # ── Commit Transaction ──────────────────────────────────────────
            await db.commit()
            
            logger.success(f"✓ Seed committed successfully: project_id={project_id}")
            
            return CommitResponse(
                project_id=project_id,
                project_name=seed.dna.title,
                agents_created=len(agent_map),
                entities_created=len(entity_map),
                goals_created=goals_created,
                relationships_created=relationships_created,
                hidden_facts_seeded=len(seed.hidden_facts),
                ready_to_simulate=True,
                suggested_steps=seed.dna.recommended_step_count,
                message=f"World generated. Run POST /api/projects/{project_id}/simulate/step to begin.",
            )
        
        except Exception as e:
            await db.rollback()
            logger.error(f"Seed commit failed: {e}")
            raise


# Global instance
seed_committer = SeedCommitter()
