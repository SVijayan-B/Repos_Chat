from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create the async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db():
    """Dependency for FastAPI endpoints to get a DB session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables and pgvector extension."""
    async with engine.begin() as conn:
        # Enable pgvector extension
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("Enabled pgvector extension")
        except Exception as e:
            logger.warning(f"Could not enable pgvector extension (might already exist or permission error): {e}")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
