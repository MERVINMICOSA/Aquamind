from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi import Request

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.models.system import User
from app.db.enums import UserRole

from app.services.actuator_executor import ActuatorExecutor

from app.services.security_service import (
    AccessTokenError,
    decode_access_token,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


async def get_db_session(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as session:
        yield session


def _authentication_required() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> User:
    if credentials is None:
        raise _authentication_required()

    if credentials.scheme.lower() != "bearer":
        raise _authentication_required()

    try:
        claims = decode_access_token(
            credentials.credentials
        )
    except AccessTokenError as exc:
        raise _authentication_required() from exc

    user = await session.get(
        User,
        claims.user_id,
    )

    if user is None:
        raise _authentication_required()

    if not user.is_active:
        raise _authentication_required()

    return user

async def require_admin(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user

# ============================================================
# ACTUATOR EXECUTOR
# ============================================================


def get_actuator_executor(
    request: Request,
) -> ActuatorExecutor | None:
    """
    Return the application-configured actuator executor.

    Phase 8 keeps hardware execution optional.

    Until Phase 9 installs a concrete hardware executor,
    sensor ingestion continues normally without pretending
    that actuator commands succeeded.
    """

    return getattr(
        request.app.state,
        "actuator_executor",
        None,
    )