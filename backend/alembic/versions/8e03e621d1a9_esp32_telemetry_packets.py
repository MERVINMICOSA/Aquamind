"""Store ESP32 schema v1 telemetry packets without altering sensor automation.

Revision ID: 8e03e621d1a9
Revises: 4c7a9e2f1b63
"""

from alembic import op
import sqlalchemy as sa

revision = "8e03e621d1a9"
down_revision = "4c7a9e2f1b63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esp32_telemetry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "system_id", sa.Uuid(),
            sa.ForeignKey("aquaponics_systems.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("uptime_ms", sa.BigInteger(), nullable=False),
        sa.Column("packet", sa.JSON(), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_esp32_telemetry"),
        sa.UniqueConstraint(
            "system_id", "device_id", "sequence", "uptime_ms",
            name="uq_esp32_telemetry_identity",
        ),
    )
    op.create_index(
        "ix_esp32_telemetry_system_received",
        "esp32_telemetry", ["system_id", "received_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_esp32_telemetry_system_received", table_name="esp32_telemetry",
    )
    op.drop_table("esp32_telemetry")
