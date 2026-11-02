from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db_session,
    require_admin,
)
from app.models.automation import AutomationRule
from app.models.system import (
    AquaponicsSystem,
    User,
)
from app.schemas.automation_rule import (
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
)
from app.services.audit_service import (
    AuditAction,
    create_audit_log,
)


router = APIRouter(
    prefix="/automation-rules",
    tags=["automation-rules"],
)


# ============================================================
# AUDIT HELPERS
# ============================================================


def _audit_value(
    value,
):
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            str(key): _audit_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _audit_value(item)
            for item in value
        ]

    return value


def _automation_rule_audit_snapshot(
    rule: AutomationRule,
) -> dict:
    return {
        "system_id": _audit_value(
            rule.system_id
        ),
        "name": _audit_value(
            rule.name
        ),
        "description": _audit_value(
            rule.description
        ),
        "trigger_type": _audit_value(
            rule.trigger_type
        ),
        "condition_definition": (
            _audit_value(
                rule.condition_definition
            )
        ),
        "action_definition": (
            _audit_value(
                rule.action_definition
            )
        ),
        "enabled": _audit_value(
            rule.enabled
        ),
        "priority": _audit_value(
            rule.priority
        ),
        "cooldown_seconds": _audit_value(
            rule.cooldown_seconds
        ),
    }


# ============================================================
# READ
# ============================================================


@router.get(
    "",
    response_model=list[AutomationRuleResponse],
)
async def list_automation_rules(
    system_id: UUID | None = None,
    enabled: bool | None = None,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    query = (
        select(AutomationRule)
        .order_by(
            AutomationRule.priority.desc(),
            AutomationRule.name,
        )
    )

    if system_id is not None:
        query = query.where(
            AutomationRule.system_id
            == system_id
        )

    if enabled is not None:
        query = query.where(
            AutomationRule.enabled
            == enabled
        )

    result = await session.execute(
        query
    )

    return result.scalars().all()


@router.get(
    "/{rule_id}",
    response_model=AutomationRuleResponse,
)
async def get_automation_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
):
    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found",
        )

    return rule


# ============================================================
# CREATE
# ============================================================


@router.post(
    "",
    response_model=AutomationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_automation_rule(
    payload: AutomationRuleCreate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    system = await session.get(
        AquaponicsSystem,
        payload.system_id,
    )

    if (
        system is None
        or system.deleted_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aquaponics system not found",
        )

    rule = AutomationRule(
        system_id=payload.system_id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        condition_definition=(
            payload.condition_definition
        ),
        action_definition=(
            payload.action_definition
        ),
        enabled=payload.enabled,
        priority=payload.priority,
        cooldown_seconds=(
            payload.cooldown_seconds
        ),
    )

    session.add(
        rule
    )

    await session.commit()
    await session.refresh(
        rule
    )

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="automation_rule",
        entity_id=rule.id,
        new_value=(
            _automation_rule_audit_snapshot(
                rule
            )
        ),
    )

    return rule


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{rule_id}",
    response_model=AutomationRuleResponse,
)
async def update_automation_rule(
    rule_id: UUID,
    payload: AutomationRuleUpdate,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found",
        )

    updates = payload.model_dump(
        exclude_unset=True
    )

    old_value = {
        field: _audit_value(
            getattr(
                rule,
                field,
            )
        )
        for field in updates
    }

    for field, value in updates.items():
        setattr(
            rule,
            field,
            value,
        )

    await session.commit()
    await session.refresh(
        rule
    )

    new_value = {
        field: _audit_value(
            getattr(
                rule,
                field,
            )
        )
        for field in updates
    }

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="automation_rule",
        entity_id=rule.id,
        old_value=old_value,
        new_value=new_value,
    )

    return rule


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_automation_rule(
    rule_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
    current_user: User = Depends(
        require_admin
    ),
):
    rule = await session.get(
        AutomationRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation rule not found",
        )

    old_value = (
        _automation_rule_audit_snapshot(
            rule
        )
    )

    entity_id = rule.id

    await session.delete(
        rule
    )

    await session.commit()

    await create_audit_log(
        session,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="automation_rule",
        entity_id=entity_id,
        old_value=old_value,
        new_value=None,
    )