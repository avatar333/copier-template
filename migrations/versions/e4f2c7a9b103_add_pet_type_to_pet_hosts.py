"""Add pet_type to pet_hosts

Revision ID: e4f2c7a9b103
Revises: d7e5b2c4a901
Create Date: 2026-06-10 09:15:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "e4f2c7a9b103"
down_revision = "d7e5b2c4a901"
branch_labels = None
depends_on = None

PET_TYPE_NON_PRODUCTION = "non_production"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("pet_hosts")}

    if "pet_type" not in existing_columns:
        op.add_column(
            "pet_hosts",
            sa.Column("pet_type", sa.String(length=32), nullable=True),
        )
    bind.execute(
        sa.text(
            "UPDATE pet_hosts SET pet_type = :pet_type WHERE pet_type IS NULL"
        ),
        {"pet_type": PET_TYPE_NON_PRODUCTION},
    )
    op.alter_column(
        "pet_hosts",
        "pet_type",
        existing_type=sa.String(length=32),
        nullable=False,
    )

    unique_constraints = inspector.get_unique_constraints("pet_hosts")
    for constraint in unique_constraints:
        columns = constraint.get("column_names") or []
        name = constraint.get("name")
        if columns == ["fqdn"] and name:
            op.drop_constraint(name, "pet_hosts", type_="unique")

    refreshed_constraints = {
        constraint.get("name")
        for constraint in sa.inspect(bind).get_unique_constraints("pet_hosts")
        if constraint.get("name")
    }
    if "uq_pet_hosts_pet_type_fqdn" not in refreshed_constraints:
        op.create_unique_constraint(
            "uq_pet_hosts_pet_type_fqdn",
            "pet_hosts",
            ["pet_type", "fqdn"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    duplicate_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM (
                SELECT fqdn
                FROM pet_hosts
                GROUP BY fqdn
                HAVING COUNT(*) > 1
            ) duplicates
            """
        )
    ).scalar_one()
    if duplicate_count:
        raise RuntimeError(
            "Cannot downgrade because pet_hosts contains the same fqdn in multiple pet types."
        )

    unique_constraints = inspector.get_unique_constraints("pet_hosts")
    for constraint in unique_constraints:
        if constraint.get("name") == "uq_pet_hosts_pet_type_fqdn":
            op.drop_constraint("uq_pet_hosts_pet_type_fqdn", "pet_hosts", type_="unique")
            break

    remaining_constraints = inspector.get_unique_constraints("pet_hosts")
    if not any((constraint.get("column_names") or []) == ["fqdn"] for constraint in remaining_constraints):
        op.create_unique_constraint("uq_pet_hosts_fqdn", "pet_hosts", ["fqdn"])

    existing_columns = {column["name"] for column in inspector.get_columns("pet_hosts")}
    if "pet_type" in existing_columns:
        op.drop_column("pet_hosts", "pet_type")
