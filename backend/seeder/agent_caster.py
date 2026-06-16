"""
MapR1 — Agent Caster (Pass 3)

Casts agents with crafted personalities designed for maximum dramatic tension.
This is where the magic happens — each agent is designed like a character in a story.
"""

from typing import List, Optional
from loguru import logger
from backend.seeder.seed_models import (
    ScenarioDNA,
    EntitySeed,
    AgentSeed,
    PersonalitySeed,
)
from backend.seeder.openrouter_client import openrouter_client
from pydantic import BaseModel

class AgentCasterResponse(BaseModel):
    agents: List[AgentSeed]


AGENT_CASTING_SYSTEM_PROMPT = """You are a character director for MapR1 simulations.

Your job is to CAST agents like a film director casts actors — each agent must be designed to create maximum dramatic tension based on the scenario DNA.

**CRITICAL RULES**:
1. Every core tension must have agents on BOTH sides
2. At least one agent should be a "wildcard" (unpredictable)
3. Personalities should create natural friction (not all moderate/balanced)
4. Agent types MUST strictly be one of the provided role keys
5. Each agent needs a clear "dramatic_function": protagonist, antagonist, wildcard, catalyst
6. Personalities are NOT random — they're CRAFTED for drama
7. Every agent needs a backstory and a secret
8. Initial resources should reflect their position in the world

**Personality Traits** (all 0.0-1.0):
- Big Five: openness, conscientiousness, extraversion, agreeableness, neuroticism
- Simulation: risk_tolerance, ambition, empathy, rationality, creativity, morality

**Dramatic Functions**:
- protagonist: The "hero" driving positive change
- antagonist: The force opposing the protagonist
- wildcard: Unpredictable, could go either way
- catalyst: Triggers events but doesn't take center stage

Return valid JSON matching this schema:
{
  "agents": [
    {
      "name": "string (realistic person name)",
      "agent_type": "string (role_key from the available list)",
      "role": "string (specific title or position)",
      "entity_name": "string (links to entity)",
      "faction": "string (links to faction)",
      "dramatic_function": "string (protagonist/antagonist/wildcard/catalyst)",
      "personality": {
        "openness": float,
        "conscientiousness": float,
        "extraversion": float,
        "agreeableness": float,
        "neuroticism": float,
        "risk_tolerance": float,
        "ambition": float,
        "empathy": float,
        "rationality": float,
        "creativity": float,
        "morality": float,
        "personality_rationale": "string (why these values create drama)"
      },
      "backstory": "string (2-3 sentences)",
      "secret": "string (hidden information)",
      "initial_resources": {
        "funding": float (0.0-1.0),
        "influence": float (0.0-1.0),
        "network": float (0.0-1.0)
      },
      "initial_reputation": float (0.0-1.0)
    }
  ]
}"""


class AgentCaster:
    """Casts agents with dramatic personalities."""
    
    async def cast(
        self,
        dna: ScenarioDNA,
        entities: List[EntitySeed],
        roles: dict[str, str] = None,
        user_overrides: Optional[List] = None,
    ) -> List[AgentSeed]:
        """
        Cast agents that embody the scenario's tensions.
        
        Args:
            dna: Scenario DNA
            entities: Generated entities
            roles: Valid roles from the active theme
            user_overrides: Optional user-specified agent overrides
        
        Returns:
            List of AgentSeed objects
        """
        logger.info(f"Casting agents for '{dna.title}'...")
        
        # Build entity descriptions
        entity_descriptions = []
        for entity in entities:
            entity_descriptions.append(
                f"- **{entity.name}** ({entity.type}, faction: {entity.faction}): {entity.description}"
            )
            
        roles_str = "\n".join([f"- {k}: {v}" for k, v in (roles or {}).items()])
        
        user_prompt = f"""Cast {dna.recommended_agent_count} agents for this scenario:

**Title**: {dna.title}
**Core Tension**: {dna.core_tension}
**Secondary Tensions**: {', '.join(dna.secondary_tensions)}

**Available Entities**:
{chr(10).join(entity_descriptions)}

**Factions**:
{', '.join([f.name for f in dna.factions])}

**Available Role Keys (MUST use one of these for agent_type)**:
{roles_str}

Cast agents that will create maximum drama and conflict.
Ensure agents are on OPPOSING sides of the core tension.
Give each agent a unique personality crafted for their dramatic function."""
        
        try:
            response = await openrouter_client.generate_structured(
                response_model=AgentCasterResponse,
                prompt=user_prompt,
                system_prompt=AGENT_CASTING_SYSTEM_PROMPT,
                temperature=0.9,  # Higher temperature for more creative casting
                max_tokens=3000,
            )
            
            # Parse agents
            agents = response.agents
            
            # Apply user overrides if provided
            if user_overrides:
                for override in user_overrides:
                    if "personality" in override:
                        personality = PersonalitySeed(**override.pop("personality"))
                        agents.append(AgentSeed(**override, personality=personality))
                    else:
                        # Use default personality if not provided
                        default_personality = PersonalitySeed(
                            openness=0.5,
                            conscientiousness=0.5,
                            extraversion=0.5,
                            agreeableness=0.5,
                            neuroticism=0.5,
                            risk_tolerance=0.5,
                            ambition=0.5,
                            empathy=0.5,
                            rationality=0.5,
                            creativity=0.5,
                            morality=0.5,
                            personality_rationale="User-specified agent",
                        )
                        agents.append(AgentSeed(**override, personality=default_personality))
            
            logger.success(f"✓ Cast {len(agents)} agents with dramatic personalities")
            
            # Log dramatic functions
            functions = {}
            for agent in agents:
                functions[agent.dramatic_function] = functions.get(agent.dramatic_function, 0) + 1
            logger.info(f"  Dramatic functions: {functions}")
            
            return agents
        
        except Exception as e:
            logger.error(f"Agent casting failed: {e}")
            raise


# Global instance
agent_caster = AgentCaster()
