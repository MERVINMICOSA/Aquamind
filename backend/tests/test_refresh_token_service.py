from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.db.enums import UserRole
from app.models.system import RefreshToken, User
from app.services.refresh_token_service import (
    IssuedRefreshToken,
    RefreshTokenLifecycleError,
    RotatedRefreshToken,
    issue_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_persisted_refresh_token,
)
from app.services.security_service import (
    hash_password,
    hash_refresh_token,
)


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def configure_refresh_token_settings(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "REFRESH_TOKEN_EXPIRE_DAYS",
        7,
    )


# ============================================================
# HELPERS
# ============================================================


async def create_user(
    session,
    *,
    username="admin",
    is_active=True,
):
    user = User(
        username=username,
        password_hash=hash_password(
            "AquaMindAdmin123!"
        ),
        role=UserRole.ADMIN,
        is_active=is_active,
    )

    session.add(user)

    await session.commit()
    await session.refresh(user)

    return user


# ============================================================
# ISSUE
# ============================================================


async def test_issue_refresh_token(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
        issued_at=issued_at,
    )

    assert isinstance(
        issued,
        IssuedRefreshToken,
    )

    assert issued.user_id == user.id
    assert issued.token

    assert issued.issued_at == issued_at

    assert issued.expires_at == (
        issued_at
        + timedelta(days=7)
    )

    record = await test_session.get(
        RefreshToken,
        issued.record_id,
    )

    assert record is not None

    assert (
        record.token_hash
        == hash_refresh_token(
            issued.token
        )
    )

    assert record.token_hash != issued.token
    assert record.revoked_at is None


async def test_issue_refresh_token_rejects_missing_user(
    test_session,
):
    with pytest.raises(
        RefreshTokenLifecycleError,
        match="User not found",
    ):
        await issue_refresh_token(
            test_session,
            user_id=UUID(
                "00000000-0000-0000-0000-000000000000"
            ),
        )


async def test_issue_refresh_token_rejects_inactive_user(
    test_session,
):
    user = await create_user(
        test_session,
        is_active=False,
    )

    with pytest.raises(
        RefreshTokenLifecycleError,
        match="User is inactive",
    ):
        await issue_refresh_token(
            test_session,
            user_id=user.id,
        )


# ============================================================
# VALIDATION
# ============================================================


async def test_valid_refresh_token_is_accepted(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
        issued_at=issued_at,
    )

    validated = (
        await validate_persisted_refresh_token(
            test_session,
            token=issued.token,
            current_time=(
                issued_at
                + timedelta(days=1)
            ),
        )
    )

    assert (
        validated.record_id
        == issued.record_id
    )

    assert validated.user_id == user.id


async def test_unknown_refresh_token_is_rejected(
    test_session,
):
    with pytest.raises(
        RefreshTokenLifecycleError,
        match="Refresh token is invalid",
    ):
        await validate_persisted_refresh_token(
            test_session,
            token="not-a-real-refresh-token",
            current_time=datetime.now(
                timezone.utc
            ),
        )


async def test_expired_refresh_token_is_rejected(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
        issued_at=issued_at,
    )

    with pytest.raises(
        RefreshTokenLifecycleError,
        match="Refresh token has expired",
    ):
        await validate_persisted_refresh_token(
            test_session,
            token=issued.token,
            current_time=(
                issued.expires_at
            ),
        )


async def test_inactive_user_invalidates_existing_refresh_token(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
    )

    user.is_active = False

    await test_session.commit()

    with pytest.raises(
        RefreshTokenLifecycleError,
        match=(
            "Refresh token user is inactive"
        ),
    ):
        await validate_persisted_refresh_token(
            test_session,
            token=issued.token,
            current_time=datetime.now(
                timezone.utc
            ),
        )


# ============================================================
# REVOCATION
# ============================================================


async def test_revoke_refresh_token(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
        issued_at=issued_at,
    )

    revoked_at = (
        issued_at
        + timedelta(hours=1)
    )

    revoked = await revoke_refresh_token(
        test_session,
        token=issued.token,
        revoked_at=revoked_at,
    )

    assert (
        revoked.record_id
        == issued.record_id
    )

    assert revoked.revoked_at == revoked_at

    with pytest.raises(
        RefreshTokenLifecycleError,
        match="Refresh token has been revoked",
    ):
        await validate_persisted_refresh_token(
            test_session,
            token=issued.token,
            current_time=(
                revoked_at
                + timedelta(seconds=1)
            ),
        )


async def test_revoking_token_twice_is_rejected(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued = await issue_refresh_token(
        test_session,
        user_id=user.id,
    )

    await revoke_refresh_token(
        test_session,
        token=issued.token,
    )

    with pytest.raises(
        RefreshTokenLifecycleError,
        match=(
            "Refresh token has already "
            "been revoked"
        ),
    ):
        await revoke_refresh_token(
            test_session,
            token=issued.token,
        )


# ============================================================
# ROTATION
# ============================================================


async def test_rotate_refresh_token(
    test_session,
):
    user = await create_user(
        test_session
    )

    issued_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    original = await issue_refresh_token(
        test_session,
        user_id=user.id,
        issued_at=issued_at,
    )

    rotation_time = (
        issued_at
        + timedelta(hours=2)
    )

    rotated = await rotate_refresh_token(
        test_session,
        token=original.token,
        current_time=rotation_time,
    )

    assert isinstance(
        rotated,
        RotatedRefreshToken,
    )

    assert (
        rotated.revoked_record_id
        == original.record_id
    )

    assert (
        rotated.issued.record_id
        != original.record_id
    )

    assert (
        rotated.issued.token
        != original.token
    )

    assert (
        rotated.issued.user_id
        == user.id
    )

    old_record = await test_session.get(
        RefreshToken,
        original.record_id,
    )

    assert old_record is not None
    assert old_record.revoked_at is not None

    new_record = await test_session.get(
        RefreshToken,
        rotated.issued.record_id,
    )

    assert new_record is not None
    assert new_record.revoked_at is None

    validated = (
        await validate_persisted_refresh_token(
            test_session,
            token=rotated.issued.token,
            current_time=(
                rotation_time
                + timedelta(seconds=1)
            ),
        )
    )

    assert (
        validated.record_id
        == rotated.issued.record_id
    )


async def test_rotated_old_token_cannot_be_reused(
    test_session,
):
    user = await create_user(
        test_session
    )

    original = await issue_refresh_token(
        test_session,
        user_id=user.id,
    )

    await rotate_refresh_token(
        test_session,
        token=original.token,
    )

    with pytest.raises(
        RefreshTokenLifecycleError,
        match="Refresh token has been revoked",
    ):
        await validate_persisted_refresh_token(
            test_session,
            token=original.token,
            current_time=datetime.now(
                timezone.utc
            ),
        )