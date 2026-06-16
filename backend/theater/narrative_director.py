from typing import List, Optional, Any
from loguru import logger
from backend.models.action_models import ActionResponse
from backend.models.world_models import StructuredWorldState
from backend.theater.theater_models import TensionMetrics, StepNarrative
from backend.seeder.openrouter_client import OpenRouterClient
from backend.core.config import settings

# Initialize a theater-specific openrouter client using the theater model
theater_openrouter = OpenRouterClient(model_name=settings.theater_openrouter_model)

def get_narrative_system_prompt(theme_resolver: Optional[Any] = None) -> str:
    tone_str = "geopolitical thriller or sci-fi novel"
    if theme_resolver and hasattr(theme_resolver, "theme") and theme_resolver.theme:
        tone_str = theme_resolver.theme.narrative_tone

    return f"""You are a master storyteller and narrator for MapR1 simulations.

Your job is to transform raw simulation actions and tension metrics into compelling, character-driven story prose.
Treat this like a chapter in a {tone_str}. Focus on the 'why' and the emotional/strategic impact of actions, rather than just listing what happened.

**CRITICAL RULES**:
1. Output structured JSON matching the StepNarrative schema.
2. The `headline` should be punchy and dramatic.
3. The `summary` should be 2-3 paragraphs of cohesive, dramatic prose. Do NOT just list actions; weave them into a story.
4. For `agent_beats`, extract the core of what each active agent did, their emotional state, and motivation.
5. In `open_questions`, pose 1-3 dramatic questions the audience would be wondering.
6. Tone should match the `phase` (e.g., Rising Action is tense; Lull is calculating/quiet).
7. Collapsed agents permanently exit the active simulation. Limit mentions of them to ONE sentence maximum per chapter, and ONLY if another agent actively targeted them this step.
"""

class NarrativeDirector:
    """Transforms simulation data into compelling narratives."""
    
    async def narrate_step(
        self,
        step: int,
        actions: List[ActionResponse],
        tension: TensionMetrics,
        world_state: StructuredWorldState,
        previous_narrative: Optional[str],
        theme_resolver: Optional[Any] = None,
        collapsed_agents: Optional[List[str]] = None,
    ) -> StepNarrative:
        
        logger.info(f"Generating narrative for step {step}...")
        
        # Build prompt
        action_descriptions = []
        for a in actions:
            status = "Succeeded" if a.success else "Failed"
            action_descriptions.append(
                f"- **{a.agent_name}** attempted '{a.action_type}' ({status}): {a.description}. Reasoning: {a.reasoning}"
            )
            
        prompt = f"""Generate a narrative chapter for Step {step}.

**Tension Context**:
- Overall Tension: {tension.overall_tension:.2f}/1.0
- Phase: {tension.phase.value}
- Climax Candidate: {tension.is_climax_candidate}

**What Happened This Step**:
{chr(10).join(action_descriptions)}

**Collapsed Agents**:
{', '.join(collapsed_agents) if collapsed_agents else "None"}

**Previous Context**:
{previous_narrative or "This is the beginning of the story."}

Write a compelling chapter that captures the drama and strategic movements of this step."""

        try:
            narrative = await theater_openrouter.generate_structured(
                response_model=StepNarrative,
                prompt=prompt,
                system_prompt=get_narrative_system_prompt(theme_resolver),
                temperature=0.8,
            )
            logger.success(f"Generated narrative: '{narrative.headline}'")
            return narrative
        except Exception as e:
            logger.error(f"Failed to generate narrative: {e}")
            # Fallback narrative
            return StepNarrative(
                step=step,
                phase=tension.phase.value,
                headline="A Turn of Events",
                summary="The simulation advanced, but the narrator encountered an error recording the events.",
                agent_beats=[],
                open_questions=["What will happen next?"]
            )

# Global instance
narrative_director = NarrativeDirector()
