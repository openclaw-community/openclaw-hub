"""
Database initialization and connection management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .models import Base
import structlog

logger = structlog.get_logger()

DATABASE_URL = "sqlite+aiosqlite:///./aigateway.db"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure the `provider` column exists in the `requests` table.
        # SQLAlchemy create_all does not add columns to existing tables, so we
        # handle this migration manually with a safe ALTER TABLE (SQLite supports
        # ADD COLUMN but not IF EXISTS, so we catch the error gracefully).
        try:
            await conn.execute(text("ALTER TABLE requests ADD COLUMN provider VARCHAR"))
            logger.info("requests_provider_column_added")
        except Exception:
            # Column already exists — this is expected on subsequent starts
            pass

    logger.info("database_initialized", url=DATABASE_URL)


async def backfill_provider_column():
    """
    One-time backfill: set provider for existing requests based on model name pattern.
    Idempotent — only updates rows where provider IS NULL.
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                "UPDATE requests SET provider = CASE "
                "WHEN model LIKE 'gpt%' THEN 'openai' "
                "WHEN model LIKE 'claude%' THEN 'anthropic' "
                "ELSE 'ollama' "
                "END WHERE provider IS NULL"
            )
        )
        await session.commit()
        count = result.rowcount
        if count > 0:
            logger.info("provider_column_backfilled", rows=count)
            print(f"[Dashboard] Backfilled provider column for {count} existing request rows.")


async def get_session() -> AsyncSession:
    """Dependency for getting database sessions"""
    async with async_session() as session:
        yield session
