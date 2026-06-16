"""
MapR1 — DNA Extractor (Pass 0)

Extracts structured "Scenario DNA" from a user's "what if" prompt.
This is the foundation for all subsequent generation passes.
"""

from loguru import logger
from backend.seeder.seed_models import ScenarioDNA, FactionBlueprint
from backend.seeder.openrouter_client import openrouter_client


DNA_EXTRACTION_SYSTEM_PROMPT = """You are a scenario architect for MapR1, a multi-agent simulation system.

Your job is to analyze a user's "what if" prompt and extract the SCENARIO DNA — the genetic code that will be used to generate a complete simulation world.

You must identify:
1. **Core Tension**: The central conflict that drives the scenario
2. **Factions**: The major groups/sides in this conflict (3-5 factions)
3. **Themes**: The domains this scenario touches
4. **Complexity**: How many agents and steps are needed to explore this scenario

**CRITICAL RULES**:
- Every scenario needs OPPOSING factions (conflict is essential)
- Factions should have clear motivations and vulnerabilities
- The core tension should be a question with no easy answer
- Recommended agent count: 3-8 (more complex scenarios need more agents)
- Recommended step count: 6-20 (longer for slow-burn scenarios)
- Intensity: 0.0-1.0 (how volatile/fast-moving is this scenario?)

**THEME CONSTRAINTS**:
You must align the scenario DNA with the provided theme conflicts and narrative tone.
"""


class DNAExtractor:
    """Extracts scenario DNA from user prompts."""
    
    async def extract(
        self,
        prompt: str,
        conflicts: dict[str, str] = None,
        narrative_tone: str = "Neutral"
    ) -> ScenarioDNA:
        """
        Extract scenario DNA from a user's "what if" prompt.
        
        Args:
            prompt: User's scenario prompt
            conflicts: Valid core conflicts from the active theme
            narrative_tone: The tone of the scenario
        
        Returns:
            ScenarioDNA object
        """
        logger.info(f"Extracting DNA from prompt: {prompt[:100]}...")
        
        conflicts_str = "\n".join([f"- {k}: {v}" for k, v in (conflicts or {}).items()])
        
        user_prompt = f"""Analyze this scenario prompt and extract its DNA:

"{prompt}"

**Active Narrative Tone**: {narrative_tone}
**Available Core Conflicts**:
{conflicts_str}

Ensure the core tension and factions reflect the active narrative tone and available conflicts.
Provide a complete scenario DNA analysis as JSON."""
        
        try:
            dna = await openrouter_client.generate_structured(
                response_model=ScenarioDNA,
                prompt=user_prompt,
                system_prompt=DNA_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.8,
                max_tokens=2000,
            )
            
            logger.success(
                f"✓ DNA extracted: '{dna.title}' "
                f"({len(dna.factions)} factions, {dna.recommended_agent_count} agents, "
                f"{dna.recommended_step_count} steps)"
            )
            
            return dna
        
        except Exception as e:
            logger.error(f"DNA extraction failed: {e}")
            raise


# Global instance
dna_extractor = DNAExtractor()
