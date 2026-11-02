from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_db_session,
)
from app.models.system import User
from app.schemas.auth import (
    AuthTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)
from app.services.authentication_service import (
    AuthenticationError,
    authenticate_user,
    logout_user,
    refresh_authentication,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# ============================================================
# RESPONSE MAPPING
# ============================================================


def _build_token_response(
    result,
) -> AuthTokenResponse:
    return AuthTokenResponse(
        user_id=result.user_id,
        username=result.username,
        role=result.role,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        refresh_token_expires_at=(
            result.refresh_token_expires_at
        ),
    )


# ============================================================
# LOGIN
# ============================================================


@router.post(
    "/login",
    response_model=AuthTokenResponse,
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> AuthTokenResponse:
    try:
        result = await authenticate_user(
            session,
            username=payload.username,
            password=payload.password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid username or password"
            ),
            headers={
                "WWW-Authenticate": "Bearer"
            },
        ) from exc

    await create_audit_log(
        session,
        user_id=result.user_id,
        action=AuditAction.LOGIN,
        entity_type="user",
        entity_id=result.user_id,
    )

    return _build_token_response(
        result
    )


# ============================================================
# REFRESH
# ============================================================


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
)
async def refresh(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> AuthTokenResponse:
    try:
        result = await refresh_authentication(
            session,
            refresh_token=(
                payload.refresh_token
            ),
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid refresh token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        ) from exc

    await create_audit_log(
        session,
        user_id=result.user_id,
        action=AuditAction.REFRESH,
        entity_type="user",
        entity_id=result.user_id,
    )

    return _build_token_response(
        result
    )


# ============================================================
# LOGOUT
# ============================================================


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> Response:
    logged_out_user_id: UUID | None = None

    try:
        logged_out_user_id = (
            await logout_user(
                session,
                refresh_token=(
                    payload.refresh_token
                ),
            )
        )
    except AuthenticationError:
        # Logout remains intentionally idempotent from the
        # HTTP client's perspective. Invalid, expired, or
        # already-revoked token state is not exposed.
        pass

    if logged_out_user_id is not None:
        await create_audit_log(
            session,
            user_id=logged_out_user_id,
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=logged_out_user_id,
        )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )


# ============================================================
# CURRENT USER
# ============================================================


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
async def get_me(
    current_user: User = Depends(
        get_current_user
    ),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )