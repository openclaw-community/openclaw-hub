"""
Database initialization and connection management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
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
    logger.info("database_initialized", url=DATABASE_URL)


async def get_session() -> AsyncSession:
    """Dependency for getting database sessions"""
    async with async_session() as session:
        yield session
