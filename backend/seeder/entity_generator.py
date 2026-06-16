"""
MapR1 — Entity Generator (Pass 2)

Generates entities (companies, nations, organizations) from faction blueprints.
"""

from typing import List, Optional, Tuple
from loguru import logger
from backend.seeder.seed_models import (
    ScenarioDNA,
    EntitySeed,
    EntityRelationshipSeed,
)
from backend.seeder.openrouter_client import openrouter_client
from pydantic import BaseModel

class EntityGeneratorResponse(BaseModel):
    entities: List[EntitySeed]
    relationships: List[EntityRelationshipSeed]


ENTITY_GENERATION_SYSTEM_PROMPT = """You are an entity generator for MapR1 simulations.

Given scenario DNA with faction blueprints, generate concrete entities that embody each faction.

**CRITICAL RULES**:
- Each faction should produce 1-2 concrete entities
- Entities should have realistic names (not generic placeholders)
- Entity types MUST strictly be one of the provided institution keys
- Attributes should include: influence_level, founding_year, etc.
- Generate entity-to-entity relationships (rival, alliance, trade_partner, etc.)
- Relationships should create natural tension and conflict

Return valid JSON matching this schema:
{
  "entities": [
    {
      "name": "string (realistic entity name)",
      "type": "string (institution_key from the available list)",
      "faction": "string (which faction blueprint)",
      "description": "string (1-2 sentences)",
      "attributes": {
        "influence_level": "string (low/medium/high)",
        "founding_year": integer
      }
    }
  ],
  "relationships": [
    {
      "entity_a": "string (entity name)",
      "entity_b": "string (entity name)",
      "relationship_type": "string (rival/alliance/trade_partner/etc.)",
      "strength": "string (weak/medium/strong)",
      "description": "string (why this relationship exists)"
    }
  ]
}"""


class EntityGenerator:
    """Generates entities from faction blueprints."""
    
    async def generate(
        self,
        dna: ScenarioDNA,
        institutions: dict[str, str] = None,
        user_overrides: Optional[List] = None,
    ) -> Tuple[List[EntitySeed], List[EntityRelationshipSeed]]:
        """
        Generate entities and their relationships from scenario DNA.
        
        Args:
            dna: Scenario DNA
            institutions: Valid institutions from the active theme
            user_overrides: Optional user-specified entity overrides
        
        Returns:
            Tuple of (entities, entity_relationships)
        """
        logger.info(f"Generating entities for '{dna.title}'...")
        
        # Build faction descriptions
        faction_descriptions = []
        for faction in dna.factions:
            faction_descriptions.append(
                f"- **{faction.name}** ({faction.archetype}): {faction.motivation}. "
                f"Stance: {faction.stance_on_core_tension}. "
                f"Resource: {faction.key_resource}. Vulnerability: {faction.vulnerability}."
            )
            
        institutions_str = "\n".join([f"- {k}: {v}" for k, v in (institutions or {}).items()])
        
        user_prompt = f"""Generate concrete entities for this scenario:

**Title**: {dna.title}
**Core Tension**: {dna.core_tension}

**Factions**:
{chr(10).join(faction_descriptions)}

**Available Institution Keys (MUST use one of these for the entity type)**:
{institutions_str}

Create 1-2 entities per faction with realistic names and attributes.
Also generate relationships between entities that create tension."""
        
        try:
            response = await openrouter_client.generate_structured(
                response_model=EntityGeneratorResponse,
                prompt=user_prompt,
                system_prompt=ENTITY_GENERATION_SYSTEM_PROMPT,
                temperature=0.8,
                max_tokens=2000,
            )
            
            # Parse entities
            entities = response.entities
            
            # Parse relationships
            relationships = response.relationships
            
            # Apply user overrides if provided
            if user_overrides:
                for override in user_overrides:
                    entities.append(EntitySeed(**override))
            
            logger.success(
                f"✓ Generated {len(entities)} entities and {len(relationships)} relationships"
            )
            
            return entities, relationships
        
        except Exception as e:
            logger.error(f"Entity generation failed: {e}")
            raise


# Global instance
entity_generator = EntityGenerator()
