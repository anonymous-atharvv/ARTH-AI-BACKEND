# backend/database.py
"""
SQLAlchemy async engine and session factory.
Supports PostgreSQL (production) and SQLite (demo/dev).
"""
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import structlog

from config import settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    pass


# Create async engine — SQLite for dev, PostgreSQL for production
if "sqlite" in settings.DATABASE_URL:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.LOG_LEVEL == "DEBUG",
        connect_args=settings.DATABASE_CONNECT_ARGS,
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.LOG_LEVEL == "DEBUG",
        connect_args=settings.DATABASE_CONNECT_ARGS,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_db_tables():
    """Create all tables on startup (for dev/demo — use migrations in production)."""
    # Explicitly import models to register them on Base.metadata before creation
    from models import (
        User, Transaction, Category, ArthScoreHistory,
        Document, WhatsAppSession, AnalyticsCache, InsightLog
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


async def get_db():
    """Dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
