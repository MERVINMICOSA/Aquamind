from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.other import AuditLog
from app.services.audit_service import (
    AuditAction,
    AuditServiceError,
    AuditSource,
    create_audit_log,
)


pytestmark = pytest.mark.asyncio


async def test_create_audit_log(
    test_session,
):
    user_id = uuid4()
    entity_id = uuid4()

    created_at = datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    # user_id is nullable in the model, but when supplied it
    # must satisfy the FK. Use None here because this test
    # focuses only on audit persistence.
    record = await create_audit_log(
        test_session,
        user_id=None,
        action=AuditAction.CREATE,
        entity_type="sensor",
        entity_id=entity_id,
        new_value={
            "enabled": True,
        },
        source=AuditSource.API,
        created_at=created_at,
    )

    assert isinstance(
        record,
        AuditLog,
    )

    assert record.id is not None
    assert record.user_id is None
    assert record.action == "create"
    assert record.entity_type == "sensor"
    assert record.entity_id == entity_id

    assert record.old_value is None

    assert record.new_value == {
        "enabled": True,
    }

    assert record.source == "api"


async def test_audit_log_accepts_user_id(
    test_session,
):
    from app.db.enums import UserRole
    from app.models.system import User
    from app.services.security_service import (
        hash_password,
    )

    user = User(
        username="audit-admin",
        password_hash=hash_password(
            "AquaMindAdmin123!"
        ),
        role=UserRole.ADMIN,
        is_active=True,
    )

    test_session.add(user)

    await test_session.commit()
    await test_session.refresh(user)

    record = await create_audit_log(
        test_session,
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="system",
        entity_id=uuid4(),
    )

    assert record.user_id == user.id


async def test_audit_log_accepts_old_and_new_values(
    test_session,
):
    record = await create_audit_log(
        test_session,
        user_id=None,
        action=AuditAction.UPDATE,
        entity_type="tank",
        entity_id=uuid4(),
        old_value={
            "name": "Tank A",
        },
        new_value={
            "name": "Tank B",
        },
    )

    assert record.old_value == {
        "name": "Tank A",
    }

    assert record.new_value == {
        "name": "Tank B",
    }


async def test_audit_action_enum_values_are_stable():
    assert AuditAction.CREATE.value == "create"
    assert AuditAction.UPDATE.value == "update"
    assert AuditAction.DELETE.value == "delete"
    assert (
        AuditAction.ACKNOWLEDGE.value
        == "acknowledge"
    )
    assert AuditAction.LOGIN.value == "login"
    assert AuditAction.LOGOUT.value == "logout"
    assert AuditAction.REFRESH.value == "refresh"


async def test_empty_audit_action_is_rejected(
    test_session,
):
    with pytest.raises(
        AuditServiceError,
        match="Audit action cannot be empty",
    ):
        await create_audit_log(
            test_session,
            user_id=None,
            action="",
            entity_type="sensor",
        )


async def test_empty_entity_type_is_rejected(
    test_session,
):
    with pytest.raises(
        AuditServiceError,
        match=(
            "Audit entity type cannot be empty"
        ),
    ):
        await create_audit_log(
            test_session,
            user_id=None,
            action=AuditAction.CREATE,
            entity_type="",
        )


async def test_invalid_old_value_is_rejected(
    test_session,
):
    with pytest.raises(
        AuditServiceError,
        match=(
            "Audit old value must be "
            "a dictionary"
        ),
    ):
        await create_audit_log(
            test_session,
            user_id=None,
            action=AuditAction.UPDATE,
            entity_type="sensor",
            old_value="invalid",
        )


async def test_invalid_new_value_is_rejected(
    test_session,
):
    with pytest.raises(
        AuditServiceError,
        match=(
            "Audit new value must be "
            "a dictionary"
        ),
    ):
        await create_audit_log(
            test_session,
            user_id=None,
            action=AuditAction.UPDATE,
            entity_type="sensor",
            new_value="invalid",
        )


async def test_naive_audit_timestamp_is_rejected(
    test_session,
):
    with pytest.raises(
        AuditServiceError,
        match=(
            "Audit timestamp must "
            "be timezone-aware"
        ),
    ):
        await create_audit_log(
            test_session,
            user_id=None,
            action=AuditAction.CREATE,
            entity_type="sensor",
            created_at=datetime(
                2026,
                1,
                1,
                12,
                0,
                0,
            ),
        )