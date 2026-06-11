"""Merge assignment-run pool metadata and nullable host assignment branches

Revision ID: 8f4b5c2d7a91
Revises: 2d8f0b6d9d10, c1b8d9f0a2c4
Create Date: 2026-06-09 15:30:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "8f4b5c2d7a91"
down_revision = ("2d8f0b6d9d10", "c1b8d9f0a2c4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge revision only; no schema changes are required."""


def downgrade() -> None:
    """Split the branch heads again on downgrade."""

