from typing import List
from uuid import UUID
from loguru import logger

from backend.theater.theater_models import StepNarrative, SimulationStory, CharacterArc, TensionMetrics
from backend.seeder.seed_models import ScenarioDNA
from backend.seeder.openrouter_client import OpenRouterClient
from backend.core.config import settings

theater_openrouter = OpenRouterClient(model_name=settings.theater_openrouter_model)

EPILOGUE_SYSTEM_PROMPT = """You are a master storyteller and narrator for MapR1 simulations.
Your job is to read the chapters of a completed simulation and write a compelling Epilogue.
Summarize the aftermath, the changed world, and what the future holds. The tone should be cinematic and reflective.
"""

class StoryCompiler:
    """Compiles individual step narratives into a complete, cohesive story document."""
    
    async def compile(
        self,
        project_id: UUID,
        title: str,
        prologue: str,
        narratives: List[StepNarrative],
        tension_arc: List[TensionMetrics]
    ) -> SimulationStory:
        
        logger.info(f"Compiling story for project {project_id}...")
        
        # 1. Generate Epilogue
        story_text = "\n\n".join([f"Chapter {n.step}: {n.headline}\n{n.summary}" for n in narratives])
        
        prompt = f"""The simulation has concluded. Here is the story so far:
{story_text}

Write a 2-3 paragraph Epilogue concluding this story."""

        epilogue = "The simulation ended before a proper conclusion could be reached."
        try:
            # We just want a string back, but openrouter_client uses instructor with models
            # So we create a quick inline model
            from pydantic import BaseModel
            class EpilogueResponse(BaseModel):
                epilogue_text: str
                
            response = await theater_openrouter.generate_structured(
                response_model=EpilogueResponse,
                prompt=prompt,
                system_prompt=EPILOGUE_SYSTEM_PROMPT,
                temperature=0.8,
            )
            epilogue = response.epilogue_text
        except Exception as e:
            logger.error(f"Failed to generate epilogue: {e}")
            
        # 2. Extract basic Character Arcs (simplified for now)
        agents_seen = set()
        for n in narratives:
            for b in n.agent_beats:
                agents_seen.add(b.agent_name)
                
        arcs = []
        for agent in agents_seen:
            arcs.append(CharacterArc(
                agent_name=agent,
                role="Participant",
                starting_position="Unknown",
                ending_position="Unknown",
                key_moments=[],
                arc_type="survivor"
            ))
            
        # 3. Create the Story Object
        story = SimulationStory(
            title=title,
            prologue=prologue,
            chapters=narratives,
            epilogue=epilogue,
            character_arcs=arcs,
            themes_explored=["Power", "Consequence", "Strategy"],
            key_insights=["The simulation revealed the fragility of the initial state."],
            tension_arc=[t.overall_tension for t in tension_arc],
            total_actions=len(narratives) * 3, # rough estimate
            total_patterns=0,
            timelines_explored=1
        )
        
        logger.success("Story compilation complete.")
        return story
        
    def export_to_markdown(self, story: SimulationStory, filepath: str):
        """Export the story to a beautiful markdown file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {story.title}\n\n")
            
            f.write("## Prologue\n")
            f.write(f"*{story.prologue}*\n\n")
            f.write("---\n\n")
            
            for chapter in story.chapters:
                f.write(f"## Chapter {chapter.step}: {chapter.headline}\n")
                f.write(f"**Tension Phase:** {chapter.phase.replace('_', ' ').title()}\n\n")
                f.write(f"{chapter.summary}\n\n")
                
                f.write("> **Key Moves:**\n")
                for beat in chapter.agent_beats:
                    f.write(f"> - **{beat.agent_name}**: {beat.action_summary}\n")
                f.write("\n---\n\n")
                
            f.write("## Epilogue\n")
            f.write(f"{story.epilogue}\n\n")
            f.write("---\n\n")
            
            f.write("## Simulation Analytics\n")
            f.write(f"- **Steps Run**: {len(story.chapters)}\n")
            f.write(f"- **Max Tension Reached**: {max(story.tension_arc, default=0.0):.2f}\n")
            
        logger.info(f"Story exported to {filepath}")

    def export_agent_diaries(self, diary_log: dict, output_dir: str, project_id: UUID, theme_resolver=None):
        import os
        import re
        
        diaries_dir = os.path.join(output_dir, "diaries")
        os.makedirs(diaries_dir, exist_ok=True)
        
        for agent_id_str, entries in diary_log.items():
            if not entries:
                continue
                
            agent_name = entries[0].agent_name
            # Slugify agent name
            agent_slug = re.sub(r'[^a-z0-9]+', '_', agent_name.lower()).strip('_')
            filepath = os.path.join(diaries_dir, f"{agent_slug}.md")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f"# {agent_name} — Personal Log\n")
                f.write("### Simulation Diaries\n")
                f.write("---\n\n")
                
                for entry in entries:
                    if entry.action_taken == "COLLAPSED":
                        f.write("## Final Entry\n")
                        exit_label = "Collapsed"
                        if theme_resolver and hasattr(theme_resolver, "theme") and hasattr(theme_resolver.theme, "vocabulary_map"):
                            exit_label = theme_resolver.theme.vocabulary_map.get("collapsed", "Collapsed")
                        f.write(f"**Status:** {exit_label}\n\n")
                        f.write(f"{entry.reasoning}\n\n---\n\n")
                        continue
                        
                    f.write(f"## Step {entry.step_number}\n")
                    status_str = "Succeeded" if entry.action_succeeded else "Failed"
                    f.write(f"**Action:** {entry.action_taken} — {status_str}  \n")
                    
                    fear = f"{entry.psychology_snapshot.get('fear', 0.0):.2f}"
                    paranoia = f"{entry.psychology_snapshot.get('paranoia', 0.0):.2f}"
                    desperation = f"{entry.psychology_snapshot.get('desperation', 0.0):.2f}"
                    f.write(f"**State of mind:** fear={fear} paranoia={paranoia} desperation={desperation}  \n")
                    
                    allies_str = ", ".join(entry.allies_at_time) if entry.allies_at_time else "None"
                    f.write(f"**Allies:** {allies_str}  \n\n")
                    
                    f.write(f"{entry.reasoning}\n\n---\n\n")
        
        logger.info(f"Agent diaries exported to {diaries_dir}")

# Global instance
story_compiler = StoryCompiler()
