"""Add pool metadata to assignment runs

Revision ID: 2d8f0b6d9d10
Revises: 91df0b1c3a77
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "2d8f0b6d9d10"
down_revision = "91df0b1c3a77"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("assignment_runs")}

    if "pool_name" not in existing_columns:
        op.add_column("assignment_runs", sa.Column("pool_name", sa.String(length=50), nullable=True))
    if "pool_collection_name" not in existing_columns:
        op.add_column(
            "assignment_runs",
            sa.Column("pool_collection_name", sa.String(length=100), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("assignment_runs")}

    if "pool_collection_name" in existing_columns:
        op.drop_column("assignment_runs", "pool_collection_name")
    if "pool_name" in existing_columns:
        op.drop_column("assignment_runs", "pool_name")
