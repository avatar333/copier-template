"""Add login_name to app_users

Revision ID: 91df0b1c3a77
Revises: da3d3cc44384
Create Date: 2026-06-08 22:10:00.000000

"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


revision = "91df0b1c3a77"
down_revision = "da3d3cc44384"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("app_users")}
    if "login_name" not in columns:
        op.add_column("app_users", sa.Column("login_name", sa.String(length=100), nullable=True))

    rows = list(
        bind.execute(
            sa.text("SELECT id, first_name, last_name, login_name FROM app_users ORDER BY id")
        )
    )
    seen: set[str] = set()
    for row in rows:
        current_login = str(row.login_name or "").strip().lower()
        base_name = _slugify(f"{row.first_name}.{row.last_name}")
        candidate = current_login or base_name
        suffix = 2
        while candidate in seen:
            candidate = f"{base_name}{suffix}"
            suffix += 1
        seen.add(candidate)
        if current_login != candidate:
            bind.execute(
                sa.text("UPDATE app_users SET login_name = :login_name WHERE id = :id"),
                {"login_name": candidate, "id": row.id},
            )

    op.alter_column(
        "app_users",
        "login_name",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("app_users")
        if constraint.get("name")
    }
    if "uq_app_user_login_name" not in unique_constraints:
        op.create_unique_constraint("uq_app_user_login_name", "app_users", ["login_name"])


def downgrade():
    op.drop_constraint("uq_app_user_login_name", "app_users", type_="unique")
    op.drop_column("app_users", "login_name")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")
    return slug or "user"
