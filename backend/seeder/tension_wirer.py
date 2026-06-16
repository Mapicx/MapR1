"""
MapR1 — Tension Wirer (Pass 5)

Wires up agent-to-agent relationships based on faction dynamics and dramatic functions.
"""

from typing import List, Optional
from loguru import logger
from backend.seeder.seed_models import (
    ScenarioDNA,
    AgentSeed,
    RelationshipSeed,
)
from backend.seeder.openrouter_client import openrouter_client
from pydantic import BaseModel

class TensionWirerResponse(BaseModel):
    relationships: List[RelationshipSeed]



TENSION_WIRING_SYSTEM_PROMPT = """You are a relationship architect for MapR1 simulations.

Your job is to wire up starting relationships between agents based on their factions, dramatic functions, and the scenario's tensions.

**CRITICAL RULES**:
1. Same faction = positive relationship (ally/friend)
2. Opposing faction = negative relationship (rival/enemy)
3. Wildcards = neutral with everyone (they're unpredictable)
4. Core tension alignment — agents on opposite sides get rivalry
5. Relationship types: rival, ally, neutral, mentor, protege, friend, enemy, competitor
6. Strength: -1.0 to 1.0 (negative = hostile, positive = friendly)
7. Trust: 0.0 to 1.0 (how much they trust each other)
8. Every relationship needs a tension_source (why it exists)

**Relationship Guidelines**:
- protagonist vs antagonist = rivalry (strength: -0.7 to -0.9, trust: 0.1-0.3)
- Same faction = alliance (strength: 0.5-0.8, trust: 0.6-0.8)
- Wildcard = neutral (strength: -0.2 to 0.2, trust: 0.4-0.6)
- Catalyst can have mixed relationships

Return valid JSON matching this schema:
{
  "relationships": [
    {
      "agent_a_name": "string",
      "agent_b_name": "string",
      "relationship_type": "string (rival/ally/neutral/mentor/etc.)",
      "strength": float (-1.0 to 1.0),
      "trust": float (0.0 to 1.0),
      "tension_source": "string (why this relationship exists)"
    }
  ]
}"""


class TensionWirer:
    """Wires up agent relationships."""
    
    async def wire(
        self,
        dna: ScenarioDNA,
        agents: List[AgentSeed],
        user_overrides: Optional[List] = None,
    ) -> List[RelationshipSeed]:
        """
        Wire up starting relationships based on faction dynamics.
        
        Args:
            dna: Scenario DNA
            agents: Cast agents
            user_overrides: Optional user-specified relationship overrides
        
        Returns:
            List of RelationshipSeed objects
        """
        logger.info(f"Wiring tensions for '{dna.title}'...")
        
        # Build agent descriptions
        agent_descriptions = []
        for agent in agents:
            agent_descriptions.append(
                f"- **{agent.name}**: Faction: {agent.faction}, "
                f"Function: {agent.dramatic_function}, Role: {agent.role}"
            )
        
        user_prompt = f"""Wire up relationships for this scenario:

**Title**: {dna.title}
**Core Tension**: {dna.core_tension}

**Agents**:
{chr(10).join(agent_descriptions)}

**Factions**:
{', '.join([f.name + ' (' + f.stance_on_core_tension + ')' for f in dna.factions])}

Create relationships that reflect faction alignments and dramatic functions.
Ensure opposing factions have rivalries and same factions have alliances."""
        
        try:
            response = await openrouter_client.generate_structured(
                response_model=TensionWirerResponse,
                prompt=user_prompt,
                system_prompt=TENSION_WIRING_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse relationships
            relationships = response.relationships
            
            # Apply user overrides if provided
            if user_overrides:
                for override in user_overrides:
                    relationships.append(RelationshipSeed(**override))
            
            logger.success(f"✓ Wired {len(relationships)} relationships")
            
            # Log relationship types
            types = {}
            for rel in relationships:
                types[rel.relationship_type] = types.get(rel.relationship_type, 0) + 1
            logger.info(f"  Relationship types: {types}")
            
            return relationships
        
        except Exception as e:
            logger.error(f"Tension wiring failed: {e}")
            raise


# Global instance
tension_wirer = TensionWirer()
