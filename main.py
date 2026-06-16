"""
MapR1 — AI Imagination Engine
Entry point: starts the FastAPI application.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import health, projects, scenarios, entities, timelines, worlds, memory, agents, simulation, theater
from backend.core.config import settings
from backend.core.database import close_db, init_db

# Configure logger
logger.add(
    "logs/mapr1.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="An AI-powered imagination engine that explores possible futures and alternate realities.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router)
app.include_router(scenarios.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(timelines.router, prefix="/api")
app.include_router(worlds.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(theater.router)


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"LLM provider: {settings.llm_provider} | model: {settings.groq_model if settings.llm_provider == 'groq' else settings.ollama_model}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize database
    try:
        await init_db()
        logger.success("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application starting without database connection")

    # Initialize semantic action router (loads embedding model + pre-embeds handlers)
    try:
        from backend.simulation.action_router import action_router
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, action_router.initialize)
        if action_router.is_ready:
            logger.success("Semantic action router initialized")
        else:
            logger.warning("Semantic action router unavailable — using keyword fallback")
    except Exception as e:
        logger.error(f"Failed to initialize action router: {e}")
        logger.warning("Continuing with keyword-based action routing")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info(f"Shutting down {settings.app_name}")
    await close_db()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
