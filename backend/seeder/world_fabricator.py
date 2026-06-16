"""
MapR1 — World Fabricator (Pass 1)

Generates initial StructuredWorldState from scenario DNA.
"""

from typing import Optional, Dict
from loguru import logger
from backend.seeder.seed_models import ScenarioDNA, WorldFabric
from backend.seeder.openrouter_client import openrouter_client


WORLD_FABRIC_SYSTEM_PROMPT = """You are a world state generator for MapR1 simulations.

Given a scenario DNA, generate the initial world conditions that will serve as the starting state for the simulation.

You must generate values (0.0-1.0) for:
1. **market_conditions**: Maps provided resource keys to their availability/health (0.0-1.0)
2. **public_opinion**: Public sentiment on key topics (-1.0 to 1.0, where -1 is very negative, 1 is very positive)
3. **media_attention**: How much media coverage different topics are getting (0.0-1.0)
4. **regulatory_pressure**: Maps provided institution keys to their pressure/influence (0.0-1.0)

**CRITICAL RULES**:
- Values should reflect the scenario's starting conditions
- Create tension through imbalanced conditions (some high, some low)
- Use ONLY the provided resource keys for market_conditions
- Use ONLY the provided institution keys for regulatory_pressure
- Do not use domain-specific strings for keys in market_conditions or regulatory_pressure

Return valid JSON matching this schema:
{
  "market_conditions": {
    "resource_key": float (0.0-1.0)
  },
  "public_opinion": {
    "topic_name": float (-1.0 to 1.0)
  },
  "media_attention": {
    "topic_name": float (0.0-1.0)
  },
  "regulatory_pressure": {
    "institution_key": float (0.0-1.0)
  }
}"""


class WorldFabricator:
    """Generates initial world state from scenario DNA."""
    
    async def fabricate(
        self,
        dna: ScenarioDNA,
        resources: dict[str, str] = None,
        institutions: dict[str, str] = None,
        user_overrides: Optional[Dict] = None,
    ) -> WorldFabric:
        """
        Generate initial world conditions from scenario DNA.
        
        Args:
            dna: Scenario DNA
            resources: Valid resources from the active theme
            institutions: Valid institutions from the active theme
            user_overrides: Optional user-specified overrides
        
        Returns:
            WorldFabric object
        """
        logger.info(f"Fabricating world state for '{dna.title}'...")
        
        resources_str = "\n".join([f"- {k}: {v}" for k, v in (resources or {}).items()])
        institutions_str = "\n".join([f"- {k}: {v}" for k, v in (institutions or {}).items()])
        
        user_prompt = f"""Generate initial world conditions for this scenario:

**Title**: {dna.title}
**Premise**: {dna.premise}
**Core Tension**: {dna.core_tension}
**Themes**: {', '.join(dna.primary_themes)}
**Starting Conditions**: {dna.starting_conditions}
**Key Variables**: {', '.join(dna.key_variables)}

**Available Resource Keys (use these for market_conditions)**:
{resources_str}

**Available Institution Keys (use these for regulatory_pressure)**:
{institutions_str}

Create world state values that reflect these conditions and set up the tension."""
        
        try:
            fabric = await openrouter_client.generate_structured(
                response_model=WorldFabric,
                prompt=user_prompt,
                system_prompt=WORLD_FABRIC_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=1500,
            )
            
            # Apply user overrides if provided
            if user_overrides:
                if "market_conditions" in user_overrides:
                    fabric.market_conditions.update(user_overrides["market_conditions"])
                if "public_opinion" in user_overrides:
                    fabric.public_opinion.update(user_overrides["public_opinion"])
                if "media_attention" in user_overrides:
                    fabric.media_attention.update(user_overrides["media_attention"])
                if "regulatory_pressure" in user_overrides:
                    fabric.regulatory_pressure.update(user_overrides["regulatory_pressure"])
            
            logger.success(
                f"✓ World fabric created: "
                f"{len(fabric.market_conditions)} markets, "
                f"{len(fabric.public_opinion)} opinion topics, "
                f"{len(fabric.media_attention)} media topics"
            )
            
            return fabric
        
        except Exception as e:
            logger.error(f"World fabrication failed: {e}")
            raise


# Global instance
world_fabricator = WorldFabricator()
