"""
MapR1 — Health Check API
System health and status endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.llm_client import llm_client

router = APIRouter(tags=["Health"])


@router.get("/", summary="Root Endpoint")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "description": "AI-powered imagination engine",
    }


@router.get("/health", summary="Health Check")
async def health():
    """Basic health check"""
    return {"status": "healthy", "app": settings.app_name}


@router.get("/health/detailed", summary="Detailed Health Check")
async def detailed_health(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and LLM"""
    health_status = {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "components": {},
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }

    # Check LLM
    try:
        llm_healthy = await llm_client.check_health()
        if llm_healthy:
            health_status["components"]["llm"] = {
                "status": "healthy",
                "provider": llm_client.provider,
                "model": llm_client.model,
                "message": "LLM service operational",
            }
        else:
            health_status["status"] = "degraded"
            health_status["components"]["llm"] = {
                "status": "unhealthy",
                "provider": llm_client.provider,
                "model": llm_client.model,
                "message": f"Model '{llm_client.model}' not available",
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["llm"] = {
            "status": "unhealthy",
            "message": f"LLM health check failed: {str(e)}",
        }

    return health_status
