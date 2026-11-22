"""Keep ESP32 live state separate from periodic history.

Revision ID: d8f3b6a0192c
Revises: 8e03e621d1a9
"""
from alembic import op
import sqlalchemy as sa

revision = "d8f3b6a0192c"
down_revision = "8e03e621d1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "esp32_capture_state",
        sa.Column("system_id", sa.Uuid(), sa.ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("device_id", sa.String(64)),
        sa.Column("mode", sa.String(12), nullable=False, server_default="live"),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("window_started_at", sa.DateTime(timezone=True)),
        sa.Column("next_save_at", sa.DateTime(timezone=True)),
        sa.Column("last_saved_at", sa.DateTime(timezone=True)),
        sa.Column("last_saved_scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("latest_packet_id", sa.Uuid()),
        sa.Column("latest_sequence", sa.Integer()),
        sa.Column("latest_uptime_ms", sa.BigInteger()),
        sa.Column("latest_packet", sa.JSON()),
        sa.Column("recent_packet_hashes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("latest_received_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mode IN ('live', 'timed')", name="esp32_capture_mode"),
        sa.CheckConstraint("interval_minutes BETWEEN 1 AND 1440", name="esp32_capture_interval"),
    )


def downgrade() -> None:
    op.drop_table("esp32_capture_state")
