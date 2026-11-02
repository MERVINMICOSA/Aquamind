"""add soft delete to sensors

Revision ID: 4c7a9e2f1b63
Revises: 169672021813
Create Date: 2026-09-06

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c7a9e2f1b63"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "169672021813"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Add the nullable soft-delete timestamp expected by Sensor."""

    op.add_column(
        "sensors",
        sa.Column(
            "deleted_at",
            sa.DateTime(
                timezone=True,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove the sensor soft-delete timestamp."""

    op.drop_column(
        "sensors",
        "deleted_at",
    )