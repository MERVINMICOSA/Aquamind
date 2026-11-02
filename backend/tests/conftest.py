from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    get_current_user,
    get_db_session,
)
from app.db.base import Base
from app.db.enums import UserRole
from app.db.session import create_engine
from app.main import app
from app.models.system import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    yield engine

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.drop_all
        )

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(
    test_engine,
):
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def test_session(
    test_session_factory,
):
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    test_session_factory,
):
    async def override_get_db_session():
        async with test_session_factory() as session:
            yield session

    authenticated_user = User(
        id=uuid4(),
        username="test-admin",
        password_hash="test-password-hash",
        role=UserRole.ADMIN,
        is_active=True,
    )

    async def override_get_current_user():
        return authenticated_user

    app.dependency_overrides[
        get_db_session
    ] = override_get_db_session

    app.dependency_overrides[
        get_current_user
    ] = override_get_current_user

    transport = ASGITransport(
        app=app
    )

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client

    finally:
        app.dependency_overrides.clear()