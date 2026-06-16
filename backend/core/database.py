"""
MapR1 — Database Connection
Async SQLAlchemy setup for Supabase PostgreSQL.
"""

from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from backend.core.config import settings

# Create async engine
# Convert postgresql:// to postgresql+asyncpg://
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    echo=False,  # Disable SQL echo; use loguru for debug logging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables if needed)"""
    from backend.models.db_models import Base
    import backend.models.entity_models
    import backend.models.world_models
    import backend.models.agent_models
    import backend.models.action_models
    import backend.models.relationship_models
    import backend.models.timeline_models
    import backend.models.goal_models
    import backend.models.delayed_effects
    import backend.models.economy_models
    import backend.models.belief_models
    from backend.models.entity_models import Entity, Relationship
    from backend.models.timeline_models import Timeline, TimelineScenario
    from backend.models.world_models import WorldState, WorldEvent
    from backend.models.agent_models import Agent, AgentMemory
    from backend.models.goal_models import Goal
    from backend.models.relationship_models import AgentRelationship, AgentInteraction
    from backend.models.action_models import AgentAction, SimulationState, EmergentPattern
    from backend.models.delayed_effects import ScheduledEvent
    from backend.models.economy_models import GlobalEconomyState

    try:
        async with engine.begin() as conn:
            # Create all tables that don't exist yet
            await conn.run_sync(Base.metadata.create_all)

            # ── Safe column migrations ────────────────────────────────────────
            # Add any new columns that may not exist on already-created tables.
            # Each statement uses IF NOT EXISTS so it's idempotent.
            migrations = [
                """
                ALTER TABLE goals
                ADD COLUMN IF NOT EXISTS knowledge_score FLOAT NOT NULL DEFAULT 0.0
                """,
                """
                ALTER TABLE agents
                ADD COLUMN IF NOT EXISTS mutable_psychology JSONB NOT NULL DEFAULT '{}'::jsonb
                """,
                """
                ALTER TABLE agents
                ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'
                """,
            ]
            for sql in migrations:
                try:
                    await conn.execute(text(sql.strip()))
                    logger.debug(f"Migration applied: {sql.strip()[:60]}...")
                except Exception as e:
                    logger.warning(f"Migration skipped (may already exist): {e}")

        logger.info("Database tables created/updated successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
