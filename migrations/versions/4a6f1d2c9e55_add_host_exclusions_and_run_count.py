"""Add host exclusions and excluded host count to assignment runs

Revision ID: 4a6f1d2c9e55
Revises: f3a1c9e4b276
Create Date: 2026-06-10 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "4a6f1d2c9e55"
down_revision = "f3a1c9e4b276"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "host_exclusions" not in existing_tables:
        op.create_table(
            "host_exclusions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("fqdn", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["app_users.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by_user_id"],
                ["app_users.id"],
                ondelete="SET NULL",
            ),
            sa.UniqueConstraint("fqdn", name="uq_host_exclusions_fqdn"),
        )

    assignment_run_columns = {column["name"] for column in inspector.get_columns("assignment_runs")}
    if "excluded_host_count" not in assignment_run_columns:
        op.add_column(
            "assignment_runs",
            sa.Column(
                "excluded_host_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    assignment_run_columns = {column["name"] for column in inspector.get_columns("assignment_runs")}
    if "excluded_host_count" in assignment_run_columns:
        op.drop_column("assignment_runs", "excluded_host_count")

    existing_tables = set(inspector.get_table_names())
    if "host_exclusions" in existing_tables:
        op.drop_table("host_exclusions")
