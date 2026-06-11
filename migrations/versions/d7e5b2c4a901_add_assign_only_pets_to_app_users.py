"""Add assign_only_pets to app_users

Revision ID: d7e5b2c4a901
Revises: 8f4b5c2d7a91
Create Date: 2026-06-09 16:45:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "d7e5b2c4a901"
down_revision = "8f4b5c2d7a91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("app_users")}

    if "assign_only_pets" not in existing_columns:
        op.add_column(
            "app_users",
            sa.Column("assign_only_pets", sa.Boolean(), nullable=True, server_default=sa.false()),
        )
        op.execute(sa.text("UPDATE app_users SET assign_only_pets = 0 WHERE assign_only_pets IS NULL"))
        op.alter_column(
            "app_users",
            "assign_only_pets",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("app_users")}

    if "assign_only_pets" in existing_columns:
        op.drop_column("app_users", "assign_only_pets")
