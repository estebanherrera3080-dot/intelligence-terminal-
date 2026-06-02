"""
Async database session factory
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Convert sync URL to async (postgresql → postgresql+asyncpg)
_async_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
).replace(
    "postgresql+psycopg2://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    _async_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a DB session and closes it after the request.
    Gracefully handles the case where PostgreSQL is not available:
    the response is still served (via provider fallback), and the
    commit error is logged at DEBUG level without re-raising.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception as commit_err:
                # DB unavailable (e.g. no PostgreSQL in dev) — swallow silently.
                # The response was already generated via provider fallback.
                logger.debug(f"DB commit skipped (no connection): {commit_err}")
                try:
                    await session.rollback()
                except Exception:
                    pass
        except Exception as route_err:
            try:
                await session.rollback()
            except Exception:
                pass
            raise route_err
