"""
MapR1 — Scenario Seeder (Main Orchestrator)

Chains all generation passes together to produce a complete simulation seed.
"""

import time
from typing import Optional, Dict
from loguru import logger
from backend.seeder.seed_models import CompleteSeed, GenerateRequest
from backend.seeder.dna_extractor import dna_extractor
from backend.seeder.world_fabricator import world_fabricator
from backend.seeder.entity_generator import entity_generator
from backend.seeder.agent_caster import agent_caster
from backend.seeder.goal_weaver import goal_weaver
from backend.seeder.tension_wirer import tension_wirer


from backend.models.compiled_model import CompiledTheme

class ScenarioSeeder:
    """
    Main orchestrator for the 5-pass scenario generation pipeline.
    
    Pipeline:
    0. DNA Extraction — Extract scenario structure
    1. World Fabric — Generate initial world state
    2. Entity Generation — Create entities and relationships
    3. Agent Casting — Cast agents with dramatic personalities
    4. Goal Weaving — Assign goals and seed hidden knowledge
    5. Tension Wiring — Wire up agent relationships
    """
    
    async def generate(
        self,
        request: GenerateRequest,
        theme: CompiledTheme,
    ) -> CompleteSeed:
        """
        Generate a complete scenario seed from a user prompt.
        
        Args:
            request: Generation request with prompt and settings
            theme: The compiled theme package to drive generation
        
        Returns:
            CompleteSeed object ready for commit
        """
        start_time = time.time()
        prompt = request.prompt
        settings = request.settings or {}
        
        logger.info("=" * 80)
        logger.info(f"SCENARIO SEEDER — THEME: {theme.theme_name}")
        logger.info("=" * 80)
        logger.info(f"Prompt: {prompt}")
        logger.info("")
        
        try:
            # ── Pass 0: DNA Extraction ──────────────────────────────────────
            logger.info("Pass 0: Extracting Scenario DNA...")
            dna = await dna_extractor.extract(
                prompt,
                conflicts=theme.conflicts,
                narrative_tone=theme.narrative_tone
            )
            logger.info("")
            
            # ── Pass 1: World Fabric ────────────────────────────────────────
            logger.info("Pass 1: Fabricating World State...")
            world_fabric = await world_fabricator.fabricate(
                dna=dna,
                resources=theme.resources,
                institutions=theme.institutions,
                user_overrides=settings.get("world_state"),
            )
            logger.info("")
            
            # ── Pass 2: Entity Generation ───────────────────────────────────
            logger.info("Pass 2: Generating Entities...")
            entities, entity_relationships = await entity_generator.generate(
                dna=dna,
                institutions=theme.institutions,
                user_overrides=settings.get("entities"),
            )
            logger.info("")
            
            # ── Pass 3: Agent Casting ───────────────────────────────────────
            logger.info("Pass 3: Casting Agents...")
            agents = await agent_caster.cast(
                dna=dna,
                entities=entities,
                roles=theme.roles,
                user_overrides=settings.get("agents"),
            )
            logger.info("")
            
            # ── Pass 4: Goal Weaving ────────────────────────────────────────
            logger.info("Pass 4: Weaving Goals & Hidden Knowledge...")
            goals, hidden_facts = await goal_weaver.weave(
                dna=dna,
                agents=agents,
                entities=entities,
                victory_conditions=theme.victory_conditions,
                failure_conditions=theme.failure_conditions,
                user_overrides=settings.get("goals"),
            )
            logger.info("")
            
            # ── Pass 5: Tension Wiring ──────────────────────────────────────
            logger.info("Pass 5: Wiring Tensions...")
            relationships = await tension_wirer.wire(
                dna=dna,
                agents=agents,
                user_overrides=settings.get("relationships"),
            )
            logger.info("")
            
            # ── Assemble Complete Seed ──────────────────────────────────────
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            seed = CompleteSeed(
                dna=dna,
                world_fabric=world_fabric,
                entities=entities,
                entity_relationships=entity_relationships,
                agents=agents,
                goals=goals,
                hidden_facts=hidden_facts,
                relationships=relationships,
                estimated_tokens_used=8000,  # Rough estimate
                generation_time_ms=generation_time_ms,
                compiled_theme=theme.model_dump() if theme else {},
            )
            
            logger.success("=" * 80)
            logger.success("✓ SCENARIO SEED GENERATED")
            logger.success("=" * 80)
            logger.success(f"Title: {dna.title}")
            logger.success(f"Entities: {len(entities)}")
            logger.success(f"Agents: {len(agents)}")
            logger.success(f"Goals: {len(goals)}")
            logger.success(f"Hidden Facts: {len(hidden_facts)}")
            logger.success(f"Relationships: {len(relationships)}")
            logger.success(f"Generation Time: {generation_time_ms}ms")
            logger.success("=" * 80)
            
            return seed
        
        except Exception as e:
            logger.error(f"Scenario generation failed: {e}")
            raise


# Global instance
scenario_seeder = ScenarioSeeder()
