"""Add per-pool assign_only flags to app_users

Revision ID: f3a1c9e4b276
Revises: e4f2c7a9b103
Create Date: 2026-06-10 15:10:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "f3a1c9e4b276"
down_revision = "e4f2c7a9b103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("app_users")}

    if "assign_only_production_pets" not in existing_columns:
        op.add_column(
            "app_users",
            sa.Column(
                "assign_only_production_pets",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            ),
        )
    if "assign_only_non_production_pets" not in existing_columns:
        op.add_column(
            "app_users",
            sa.Column(
                "assign_only_non_production_pets",
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            ),
        )

    bind.execute(
        sa.text(
            """
            UPDATE app_users
            SET
                assign_only_production_pets = COALESCE(assign_only_production_pets, assign_only_pets, 0),
                assign_only_non_production_pets = COALESCE(assign_only_non_production_pets, assign_only_pets, 0)
            """
        )
    )

    op.alter_column(
        "app_users",
        "assign_only_production_pets",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    op.alter_column(
        "app_users",
        "assign_only_non_production_pets",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("app_users")}

    if "assign_only_production_pets" in existing_columns:
        op.drop_column("app_users", "assign_only_production_pets")
    if "assign_only_non_production_pets" in existing_columns:
        op.drop_column("app_users", "assign_only_non_production_pets")
