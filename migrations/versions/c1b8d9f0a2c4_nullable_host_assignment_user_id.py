"""Allow historical host assignments to outlive deleted users

Revision ID: c1b8d9f0a2c4
Revises: 91df0b1c3a77
Create Date: 2026-06-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1b8d9f0a2c4"
down_revision = "91df0b1c3a77"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "host_assignments",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM host_assignments WHERE user_id IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot downgrade because host_assignments contains NULL user_id values."
        )
    op.alter_column(
        "host_assignments",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
