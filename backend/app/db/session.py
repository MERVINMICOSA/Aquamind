from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _normalize_async_database_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    if url.startswith("sqlite://"):
        return url.replace(
            "sqlite://",
            "sqlite+aiosqlite://",
            1,
        )

    return url


def create_engine(database_url: str | None = None, **kwargs) -> AsyncEngine:
    """Create an async SQLAlchemy engine without performing schema changes."""
    url = _normalize_async_database_url(
        database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./aquamind.db")
    )
    return create_async_engine(url, **kwargs)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


def create_session_factory_from_url(
    database_url: str,
) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(database_url)
    return create_session_factory(engine)
