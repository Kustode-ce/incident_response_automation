"""
Shared Database Connection
AsyncPG database connection management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from shared.core.config import settings

# Database engine
engine = None
async_session_factory = None


async def init_db():
    """Initialize database connections"""
    global engine, async_session_factory
    
    engine = create_async_engine(
        settings.database_url,
        echo=settings.sql_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Verify connections before use
    )
    
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def close_db():
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup"""
    
    if not async_session_factory:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def check_db_health() -> Dict:
    """Check database connectivity"""
    
    try:
        if not engine:
            return {"connected": False, "error": "Database not initialized"}
        
        async with get_db_session() as session:
            await session.execute("SELECT 1")
        
        return {
            "connected": True,
            "pool_size": settings.db_pool_size,
            "url": settings.database_url.split('@')[1] if '@' in settings.database_url else "unknown"
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with get_db_session() as session:
        yield session
```

