import asyncio
import sys
import argparse
import re
import argparse
from loguru import logger

# Configure logging to keep console clean but save everything to file
logger.remove()  # Remove default console logger

def console_filter(record):
    if record["name"] == "__main__": return True
    if "backend.seeder" in record["name"] or "backend.theater" in record["name"]: return True
    if "simulation_engine" in record["name"] and "🤝" in record["message"]: return True
    if record["level"].name in ["ERROR", "CRITICAL"]: return True
    return False

logger.add(sys.stderr, filter=console_filter, level="INFO")
logger.add("full_experience.log", level="DEBUG", mode="w")

sys.path.insert(0, ".")

from backend.core.database import AsyncSessionLocal, init_db, close_db
import os
from backend.seeder.seed_models import GenerateRequest, CompleteSeed
from backend.seeder.scenario_seeder import scenario_seeder
from backend.seeder.seed_committer import seed_committer
from backend.simulation.simulation_engine import simulation_engine
from backend.theater.simulation_theater import theater
from backend.theater.theater_models import PacingMode
from backend.theater.story_compiler import story_compiler
from backend.seeder.theme_generator import theme_generator
from backend.seeder.theme_compiler import theme_compiler

async def run_experience(prompt: str, steps: int):
    logger.info("==================================================")
    logger.info("🎬 THE MapR1 FULL EXPERIENCE")
    logger.info("==================================================")
    
    # 1. Initialize DB
    await init_db()
    
    try:
        async with AsyncSessionLocal() as db:
            # 2. SEED THE SCENARIO
            logger.info("\n=== STAGE 1: SEEDING THE SCENARIO ===")
            logger.info(f"Prompt: '{prompt}'")
            
            cache_file = "seed_cache.json"
            if os.path.exists(cache_file):
                logger.warning(f"Found cached seed data in {cache_file}. Loading from disk to save tokens and time!")
                with open(cache_file, "r", encoding="utf-8") as f:
                    seed_data_json = f.read()
                seed_data = CompleteSeed.model_validate_json(seed_data_json)
                logger.success(f"Loaded Cached Seed: {seed_data.dna.title}")
            else:
                logger.info("\n=== STAGE 1A: GENERATING THEME ===")
                theme_spec = await theme_generator.generate_theme(prompt)
                compiled_theme = theme_compiler.compile(theme_spec)
                logger.success(f"Generated Theme: {compiled_theme.theme_name}")

                request = GenerateRequest(prompt=prompt)
                seed_data = await scenario_seeder.generate(request, theme=compiled_theme)
                
                # Save to cache
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(seed_data.model_dump_json())
                    
                logger.success(f"Generated and Cached Seed: {seed_data.dna.title}")
            
            # 3. COMMIT SEED (CREATE PROJECT)
            logger.info("\n=== STAGE 2: BUILDING THE WORLD ===")
            commit_response = await seed_committer.commit(db, seed_data)
            project_id = commit_response.project_id
            logger.success(f"World Built! Project ID: {project_id}")
            
            # 4. RUN THEATER SIMULATION
            logger.info("\n=== STAGE 3: THE SIMULATION THEATER ===")
            logger.info(f"Running simulation for {steps} steps in Fast-Forward mode...")
            
            # We subscribe to see the output in the console
            queue = await theater.subscribe(project_id)
            
            # Run theater in background
            theater_task = asyncio.create_task(
                theater.start_theater(db, project_id, PacingMode.AUTO_UNIFORM, max_steps=steps)
            )
            
            # Listen to events
            while True:
                payload = await queue.get()
                event_type = payload["event"]
                data = payload["data"]
                
                if event_type == "theater_start":
                    logger.info("Theater session has begun!")
                elif event_type == "step_start":
                    logger.info(f"\n--- STEP {data['step']} ---")
                elif event_type == "agent_action":
                    status = "✅" if data.get("success") else "❌"
                    logger.info(f"  {status} {data['agent']}: {data['action']}")
                elif event_type == "world_event":
                    logger.warning(f"  🌍 WORLD EVENT ({data['action']}): {data['outcome']}")
                elif event_type == "tension_update":
                    logger.info(f"  📊 Tension: {data['tension']:.2f} | Phase: {data['phase']}")
                elif event_type == "narrative":
                    logger.info(f"\n📖 CHAPTER {data['step']}: {data['headline']}")
                    logger.info(f"{data['summary']}")
                elif event_type == "divergence_point":
                    logger.warning(f"🔀 DIVERGENCE DETECTED: {data['description']}")
                elif event_type == "error":
                    logger.error(f"⚠️ Theater Error: {data['message']}")
                    # Don't break — wait for theater_complete
                elif event_type == "theater_complete":
                    logger.success(f"Theater completed after {data['steps_run']} steps.")
                    break
                    
                queue.task_done()
                
            await theater_task
            await theater.unsubscribe(project_id, queue)
            
            # 5. COMPILE THE STORY
            logger.info("\n=== STAGE 4: COMPILING THE STORY ===")
            session = theater.get_or_create_session(project_id)
            
            story = await story_compiler.compile(
                project_id=project_id,
                title=seed_data.dna.title,
                prologue=seed_data.dna.core_tension,
                narratives=session.narratives,
                tension_arc=session.history
            )
            
            # Export to markdown
            
            # Generate scenario slug
            title = seed_data.dna.title
            scenario_slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
            
            output_dir = os.path.join("output", scenario_slug)
            
            # Handle collision
            if os.path.exists(output_dir):
                output_dir = f"{output_dir}_{str(project_id)[:8]}"
                
            os.makedirs(output_dir, exist_ok=True)
            
            story_filename = os.path.join(output_dir, "story.md")
            story_compiler.export_to_markdown(story, story_filename)
            
            # Export Diaries
            diary_log = simulation_engine.diary_logs.get(project_id, {})
            # Fetch theme resolver again if needed or pass None (agent diaries will just use "Collapsed")
            story_compiler.export_agent_diaries(diary_log, output_dir, project_id)
            
            logger.success(f"\n🎉 FULL EXPERIENCE COMPLETE!")
            logger.success(f"Story saved to: {story_filename.replace(os.sep, '/')}")
            logger.success(f"Agent diaries saved to: {os.path.join(output_dir, 'diaries').replace(os.sep, '/')}/")

    finally:
        await close_db()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the MapR1 Full Experience")
    parser.add_argument("--prompt", type=str, default="What if AGI is achieved by 2029?", help="The scenario prompt")
    parser.add_argument("--steps", type=int, default=3, help="Number of steps to simulate")
    args = parser.parse_args()
    
    asyncio.run(run_experience(args.prompt, args.steps))
