"""Add alert_id foreign key to maintenance_events.

Revision ID: 0003_add_alert_id_to_maintenance
Revises: 0002_add_users_table
Create Date: 2026-09-29 19:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_alert_id_to_maintenance"
down_revision: str | None = "0002_add_users_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("maintenance_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("alert_id", sa.BigInteger(), nullable=True))
        batch_op.create_foreign_key(
            "fk_maintenance_events_alert_id",
            "alerts",
            ["alert_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_maintenance_events_alert_id", ["alert_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("maintenance_events", schema=None) as batch_op:
        batch_op.drop_index("ix_maintenance_events_alert_id")
        batch_op.drop_constraint("fk_maintenance_events_alert_id", type_="foreignkey")
        batch_op.drop_column("alert_id")
