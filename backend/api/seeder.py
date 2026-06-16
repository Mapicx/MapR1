"""
MapR1 — Seeder API Endpoints

Endpoints for auto-generating simulation scenarios from user prompts.
"""

from uuid import UUID
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.core.database import get_db
from backend.seeder.seed_models import (
    GenerateRequest,
    CompleteSeed,
    RemixRequest,
    CommitResponse,
    QuickLaunchRequest,
)
from backend.seeder.scenario_seeder import scenario_seeder
from backend.seeder.seed_committer import seed_committer


router = APIRouter(prefix="/seed", tags=["Scenario Seeder"])


# In-memory storage for generated seeds (before commit)
# In production, this should be Redis or similar
_seed_cache: Dict[UUID, CompleteSeed] = {}


@router.post("/generate", response_model=CompleteSeed)
async def generate_scenario(request: GenerateRequest):
    """
    Generate a complete scenario seed from a user prompt.
    
    This runs the 5-pass generation pipeline and returns the seed
    as a preview before committing to the database.
    
    **Example**:
    ```json
    {
      "prompt": "What if AGI is achieved by 2029?",
      "settings": {
        "agent_count": 5,
        "intensity": 0.8
      }
    }
    ```
    """
    try:
        seed = await scenario_seeder.generate(request)
        
        # Cache the seed for later commit/remix
        _seed_cache[seed.seed_id] = seed
        
        return seed
    
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/seeds/{seed_id}", response_model=CompleteSeed)
async def get_seed(seed_id: UUID):
    """
    Retrieve a previously generated seed by ID.
    """
    seed = _seed_cache.get(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    return seed


@router.put("/seeds/{seed_id}/remix", response_model=CompleteSeed)
async def remix_seed(seed_id: UUID, request: RemixRequest):
    """
    Modify parts of a generated seed before committing.
    
    **Example**:
    ```json
    {
      "agents": {
        "modify": {
          "Dr. Sarah Chen": {
            "personality": {"risk_tolerance": 0.9}
          }
        }
      },
      "world_state": {
        "regulatory_pressure": {"ai_industry": 0.8}
      }
    }
    ```
    """
    seed = _seed_cache.get(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    
    try:
        # Apply modifications
        if request.agents:
            # Handle agent modifications
            if "modify" in request.agents:
                for agent_name, modifications in request.agents["modify"].items():
                    for agent in seed.agents:
                        if agent.name == agent_name:
                            # Apply modifications
                            for key, value in modifications.items():
                                if key == "personality":
                                    for trait, trait_value in value.items():
                                        setattr(agent.personality, trait, trait_value)
                                else:
                                    setattr(agent, key, value)
        
        if request.world_state:
            # Handle world state modifications
            for key, value in request.world_state.items():
                if hasattr(seed.world_fabric, key):
                    current = getattr(seed.world_fabric, key)
                    if isinstance(current, dict):
                        current.update(value)
        
        # Update cache
        _seed_cache[seed_id] = seed
        
        logger.info(f"Remixed seed {seed_id}")
        return seed
    
    except Exception as e:
        logger.error(f"Seed remix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seeds/{seed_id}/commit", response_model=CommitResponse)
async def commit_seed(seed_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Commit a generated seed to the database, creating all entities.
    
    This creates:
    - Project
    - World state
    - Entities
    - Agents with personalities
    - Goals
    - Relationships
    - Hidden facts
    
    Returns the project_id ready for simulation.
    """
    seed = _seed_cache.get(seed_id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    
    try:
        response = await seed_committer.commit(db, seed)
        
        # Remove from cache after successful commit
        del _seed_cache[seed_id]
        
        return response
    
    except Exception as e:
        logger.error(f"Seed commit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-launch", response_model=CommitResponse)
async def quick_launch(
    request: QuickLaunchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate + commit + optionally simulate in one request.
    
    **Example**:
    ```json
    {
      "prompt": "Cold War but with AI superpowers instead of nukes",
      "auto_simulate": true,
      "max_steps": 10,
      "step_delay_seconds": 2
    }
    ```
    """
    try:
        # Generate seed
        generate_req = GenerateRequest(prompt=request.prompt, settings={})
        seed = await scenario_seeder.generate(generate_req)
        
        # Commit seed
        response = await seed_committer.commit(db, seed)
        
        # TODO: If auto_simulate is True, start simulation
        # This would require integrating with the simulation engine
        # For now, just return the commit response
        
        if request.auto_simulate:
            logger.info(
                f"Auto-simulation requested but not yet implemented. "
                f"Use POST /api/projects/{response.project_id}/simulate/step manually."
            )
        
        return response
    
    except Exception as e:
        logger.error(f"Quick launch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/seeds/{seed_id}")
async def delete_seed(seed_id: UUID):
    """Delete a cached seed."""
    if seed_id in _seed_cache:
        del _seed_cache[seed_id]
        return {"message": "Seed deleted"}
    raise HTTPException(status_code=404, detail="Seed not found")


@router.get("/seeds")
async def list_seeds():
    """List all cached seeds."""
    return {
        "seeds": [
            {
                "seed_id": str(seed.seed_id),
                "title": seed.dna.title,
                "agents": len(seed.agents),
                "entities": len(seed.entities),
            }
            for seed in _seed_cache.values()
        ]
    }
