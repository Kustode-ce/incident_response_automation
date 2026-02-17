from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings import settings
from src.models import Base

engine = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global engine, session_factory

    engine = create_async_engine(
        settings.database_url,
        echo=settings.sql_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_engine() -> None:
    if engine:
        await engine.dispose()


def get_engine():
    """Get the current database engine."""
    return engine


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for internal use)."""
    if session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")

    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")

    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def check_db_health() -> dict:
    if session_factory is None:
        return {"connected": False, "error": "Database not initialized"}

    async with get_db_session_context() as session:
        await session.execute(text("SELECT 1"))

    return {"connected": True}


def get_metadata() -> Base:
    return Base
