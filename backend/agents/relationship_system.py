"""
Relationship System Manager

Manages agent relationships, trust, influence, and interactions.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional, Tuple
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.models.relationship_models import AgentRelationship, AgentInteraction
from backend.models.agent_models import Agent


class RelationshipManager:
    """Manages agent relationships and interactions"""
    
    def __init__(self, agent_id: UUID):
        self.agent_id = agent_id
    
    async def get_relationship(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
    ) -> Optional[AgentRelationship]:
        """
        Get relationship with another agent.
        
        Relationships are bidirectional, so we check both directions.
        
        Args:
            other_agent_id: ID of the other agent
        
        Returns:
            AgentRelationship if exists, None otherwise
        """
        result = await db.execute(
            select(AgentRelationship).where(
                or_(
                    and_(
                        AgentRelationship.agent_a_id == self.agent_id,
                        AgentRelationship.agent_b_id == other_agent_id
                    ),
                    and_(
                        AgentRelationship.agent_a_id == other_agent_id,
                        AgentRelationship.agent_b_id == self.agent_id
                    )
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_relationship(
        self,
        db: AsyncSession,
        project_id: UUID,
        other_agent_id: UUID,
        relationship_type: str,
        strength: float = 0.0,
        trust: float = 0.5,
        influence: float = 0.0,
    ) -> AgentRelationship:
        """
        Create or update relationship with another agent.
        
        Args:
            project_id: Project ID
            other_agent_id: ID of the other agent
            relationship_type: Type of relationship
            strength: -1 to 1 (hostile to friendly)
            trust: 0 to 1
            influence: -1 to 1 (who influences whom)
        
        Returns:
            Created or updated AgentRelationship
        """
        existing = await self.get_relationship(db, other_agent_id)
        
        if existing:
            # Update existing
            logger.info(f"Updating relationship between {self.agent_id} and {other_agent_id}")
            existing.relationship_type = relationship_type
            existing.strength = strength
            existing.trust = trust
            existing.influence = influence
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new
            logger.info(f"Creating relationship between {self.agent_id} and {other_agent_id}")
            relationship = AgentRelationship(
                id=uuid4(),
                project_id=project_id,
                agent_a_id=self.agent_id,
                agent_b_id=other_agent_id,
                relationship_type=relationship_type,
                strength=strength,
                trust=trust,
                influence=influence,
                interaction_count=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(relationship)
            await db.commit()
            await db.refresh(relationship)
            return relationship
    
    async def record_interaction(
        self,
        db: AsyncSession,
        project_id: UUID,
        other_agent_id: UUID,
        interaction_type: str,
        description: str,
        outcome: str,
        trust_change: float = 0.0,
        strength_change: float = 0.0,
    ) -> Tuple[AgentInteraction, AgentRelationship]:
        """
        Record an interaction between agents.
        
        This updates the relationship based on the interaction.
        
        Args:
            project_id: Project ID
            other_agent_id: ID of the other agent
            interaction_type: Type of interaction
            description: What happened
            outcome: positive, negative, neutral
            trust_change: How much trust changed
            strength_change: How much strength changed
        
        Returns:
            Tuple of (AgentInteraction, updated AgentRelationship)
        """
        logger.info(f"Recording interaction between {self.agent_id} and {other_agent_id}: {interaction_type}")
        
        # Get or create relationship
        relationship = await self.get_relationship(db, other_agent_id)
        if not relationship:
            relationship = await self.create_or_update_relationship(
                db, project_id, other_agent_id, "neutral"
            )
        
        # Create interaction record
        interaction = AgentInteraction(
            id=uuid4(),
            relationship_id=relationship.id,
            interaction_type=interaction_type,
            description=description,
            outcome=outcome,
            trust_change=trust_change,
            strength_change=strength_change,
            occurred_at=datetime.utcnow(),
        )
        db.add(interaction)
        
        # Update relationship
        old_trust = relationship.trust
        old_strength = relationship.strength
        
        relationship.trust = max(0.0, min(1.0, relationship.trust + trust_change))
        relationship.strength = max(-1.0, min(1.0, relationship.strength + strength_change))
        relationship.interaction_count += 1
        relationship.last_interaction = datetime.utcnow()
        relationship.updated_at = datetime.utcnow()
        
        # Update relationship type based on strength
        if relationship.strength > 0.7:
            relationship.relationship_type = "ally"
        elif relationship.strength > 0.4:
            relationship.relationship_type = "friend"
        elif relationship.strength < -0.7:
            relationship.relationship_type = "enemy"
        elif relationship.strength < -0.4:
            relationship.relationship_type = "rival"
        elif abs(relationship.strength) < 0.2:
            relationship.relationship_type = "neutral"
        
        await db.commit()
        await db.refresh(interaction)
        await db.refresh(relationship)
        
        logger.debug(
            f"Relationship updated: trust {old_trust:.2f}→{relationship.trust:.2f}, "
            f"strength {old_strength:.2f}→{relationship.strength:.2f}"
        )
        
        return interaction, relationship
    
    async def get_all_relationships(
        self,
        db: AsyncSession,
    ) -> List[AgentRelationship]:
        """Get all relationships for this agent"""
        result = await db.execute(
            select(AgentRelationship).where(
                or_(
                    AgentRelationship.agent_a_id == self.agent_id,
                    AgentRelationship.agent_b_id == self.agent_id
                )
            ).order_by(AgentRelationship.strength.desc())
        )
        return list(result.scalars().all())
    
    async def get_relationships_by_type(
        self,
        db: AsyncSession,
        relationship_type: str,
    ) -> List[AgentRelationship]:
        """Get relationships of a specific type"""
        result = await db.execute(
            select(AgentRelationship).where(
                or_(
                    AgentRelationship.agent_a_id == self.agent_id,
                    AgentRelationship.agent_b_id == self.agent_id
                ),
                AgentRelationship.relationship_type == relationship_type
            )
        )
        return list(result.scalars().all())
    
    async def get_allies(
        self,
        db: AsyncSession,
    ) -> List[UUID]:
        """
        Get IDs of allied agents.
        
        Returns:
            List of agent IDs
        """
        relationships = await self.get_all_relationships(db)
        allies = []
        
        for rel in relationships:
            if rel.relationship_type in ["ally", "friend", "partner"] or rel.strength > 0.5:
                # Get the other agent's ID
                other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
                allies.append(other_id)
        
        logger.debug(f"Agent {self.agent_id} has {len(allies)} allies")
        return allies
    
    async def get_enemies(
        self,
        db: AsyncSession,
    ) -> List[UUID]:
        """
        Get IDs of enemy agents.
        
        Returns:
            List of agent IDs
        """
        relationships = await self.get_all_relationships(db)
        enemies = []
        
        for rel in relationships:
            if rel.relationship_type in ["enemy", "rival"] or rel.strength < -0.5:
                other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
                enemies.append(other_id)
        
        logger.debug(f"Agent {self.agent_id} has {len(enemies)} enemies")
        return enemies
    
    async def get_interactions(
        self,
        db: AsyncSession,
        other_agent_id: UUID,
        limit: int = 10,
    ) -> List[AgentInteraction]:
        """Get interaction history with another agent"""
        relationship = await self.get_relationship(db, other_agent_id)
        if not relationship:
            return []
        
        result = await db.execute(
            select(AgentInteraction)
            .where(AgentInteraction.relationship_id == relationship.id)
            .order_by(AgentInteraction.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_relationship_context(
        self,
        db: AsyncSession,
        limit: int = 10,
    ) -> str:
        """
        Build context string of relationships for LLM.
        
        Args:
            limit: Number of relationships to include
        
        Returns:
            Formatted string of relationships
        """
        relationships = await self.get_all_relationships(db)
        
        if not relationships:
            return "No relationships."
        
        context_parts = ["=== RELATIONSHIPS ==="]
        for rel in relationships[:limit]:
            other_id = rel.agent_b_id if rel.agent_a_id == self.agent_id else rel.agent_a_id
            
            # Fetch other agent's name
            other_agent = await db.get(Agent, other_id)
            other_name = other_agent.name if other_agent else str(other_id)
            
            # Emoji based on relationship type
            emoji = {
                "ally": "🤝",
                "friend": "😊",
                "enemy": "⚔️",
                "rival": "🥊",
                "neutral": "😐",
                "mentor": "👨‍🏫",
                "partner": "🤝",
            }.get(rel.relationship_type, "👤")
            
            context_parts.append(
                f"{emoji} {other_name}: {rel.relationship_type} "
                f"(strength: {rel.strength:+.1f}, trust: {rel.trust:.1f}, "
                f"interactions: {rel.interaction_count})"
            )
        
        return "\n".join(context_parts)
    
    async def get_relationship_stats(self, db: AsyncSession) -> dict:
        """Get statistics about agent's relationships"""
        relationships = await self.get_all_relationships(db)
        
        if not relationships:
            return {
                "total": 0,
                "allies": 0,
                "enemies": 0,
                "neutral": 0,
                "avg_trust": 0.0,
                "avg_strength": 0.0,
                "total_interactions": 0,
            }
        
        # Count by type
        allies = sum(1 for r in relationships if r.strength > 0.5)
        enemies = sum(1 for r in relationships if r.strength < -0.5)
        neutral = len(relationships) - allies - enemies
        
        # Calculate averages
        avg_trust = sum(r.trust for r in relationships) / len(relationships)
        avg_strength = sum(r.strength for r in relationships) / len(relationships)
        total_interactions = sum(r.interaction_count for r in relationships)
        
        return {
            "total": len(relationships),
            "allies": allies,
            "enemies": enemies,
            "neutral": neutral,
            "avg_trust": round(avg_trust, 2),
            "avg_strength": round(avg_strength, 2),
            "total_interactions": total_interactions,
        }
