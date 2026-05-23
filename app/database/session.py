from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
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
    async with engine.begin() as conn:
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("Enabled pgvector extension")
        except Exception as e:
            logger.warning(f"Could not initialize pgvector extension: {e}")
        
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas synced successfully.")