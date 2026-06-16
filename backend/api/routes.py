"""
MapR1 — API Routes
FastAPI endpoints for scenario generation.
"""

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from backend.models.llm_client import llm_client
from backend.models.scenario import ScenarioRequest, ScenarioResponse
from backend.reasoning.scenario_generator import scenario_generator
from backend.api import agents, seeder

router = APIRouter()

# Include sub-routers
router.include_router(agents.router, tags=["agents"])
router.include_router(seeder.router, tags=["seeder"])


@router.post(
    "/scenarios/generate",
    response_model=ScenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Future Scenarios",
    description="Generate multiple alternate future scenarios from a user prompt",
)
async def generate_scenarios(request: ScenarioRequest):
    """
    Generate future scenarios based on user input.

    This endpoint takes a prompt and generates multiple plausible future scenarios,
    each with a timeline of events.

    Args:
        request: ScenarioRequest containing the prompt and number of scenarios

    Returns:
        ScenarioResponse with generated scenarios

    Raises:
        HTTPException: If generation fails
    """
    try:
        logger.info(f"Received scenario request: {request.prompt[:50]}...")

        # Generate scenarios
        scenarios = await scenario_generator.generate_scenarios(
            user_input=request.prompt, num_scenarios=request.num_scenarios
        )

        if not scenarios:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate scenarios. Please try again.",
            )

        # Create response
        response = ScenarioResponse(prompt=request.prompt, scenarios=scenarios)

        logger.success(f"Generated {len(scenarios)} scenarios successfully")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during scenario generation: {str(e)}",
        )


@router.get(
    "/scenarios/health",
    status_code=status.HTTP_200_OK,
    summary="Check LLM Health",
    description="Check if Ollama is running and the model is available",
)
async def check_llm_health():
    """
    Check the health of the LLM service.

    Returns:
        Health status of Ollama and model availability
    """
    try:
        is_healthy = await llm_client.check_health()

        if is_healthy:
            return {
                "status": "healthy",
                "provider": llm_client.provider,
                "model": llm_client.model,
                "message": "LLM service is operational",
            }
        else:
            return {
                "status": "unhealthy",
                "provider": llm_client.provider,
                "model": llm_client.model,
                "message": f"Model '{llm_client.model}' not available on {llm_client.provider}",
            }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "provider": llm_client.provider,
            "model": llm_client.model,
            "message": f"LLM provider '{llm_client.provider}' is not reachable",
            "error": str(e),
        }
