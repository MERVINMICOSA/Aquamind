"""Preserve imported validation schedules and manual correction provenance."""
from datetime import timedelta, timezone
from alembic import op
import sqlalchemy as sa

revision = "5e91ab2c7d40"
down_revision = "d8f3b6a0192c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {c["name"] for c in sa.inspect(conn).get_columns("esp32_telemetry")}
    # Earlier installations may already have the optional validation_at column.
    if "validation_at" not in columns:
        op.add_column("esp32_telemetry", sa.Column("validation_at", sa.DateTime(timezone=True)))
    op.add_column("esp32_telemetry", sa.Column("correction_log", sa.JSON()))
    table = sa.table("esp32_telemetry", sa.column("id", sa.Uuid()),
                     sa.column("device_id", sa.String()), sa.column("received_at", sa.DateTime(timezone=True)),
                     sa.column("validation_at", sa.DateTime(timezone=True)))
    rows = conn.execute(sa.select(table.c.id, table.c.received_at).where(
        table.c.device_id == "test-esp32-devkit-01", table.c.validation_at.is_(None)
    )).all()
    for row in rows:
        original = row.received_at
        if original.tzinfo is None:
            original = original.replace(tzinfo=timezone.utc)
        conn.execute(table.update().where(table.c.id == row.id).values(
            validation_at=original - timedelta(hours=8)
        ))


def downgrade() -> None:
    # Do not silently discard manually documented corrections or imported schedules.
    raise RuntimeError("Restore a pre-migration backup to downgrade; corrections must be preserved.")
