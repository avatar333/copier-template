"""Initial schema

Revision ID: da3d3cc44384
Revises: 
Create Date: 2026-06-08 18:35:32.111208

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da3d3cc44384'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('app_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('first_name', 'last_name', name='uq_app_user_name')
    )
    op.create_table('assignment_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('host_count', sa.Integer(), nullable=False),
    sa.Column('user_count', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['app_users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('pet_hosts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('fqdn', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['app_users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fqdn')
    )
    op.create_table('host_assignments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assignment_run_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('fqdn', sa.String(length=255), nullable=False),
    sa.Column('source_type', sa.String(length=50), nullable=False),
    sa.Column('source_name', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['assignment_run_id'], ['assignment_runs.id']),
    sa.ForeignKeyConstraint(['user_id'], ['app_users.id']),
    sa.PrimaryKeyConstraint('id')
    ,sa.UniqueConstraint('assignment_run_id', 'fqdn', name='uq_assignment_run_fqdn')
    )
    op.create_table('assignment_warnings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('assignment_run_id', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['assignment_run_id'], ['assignment_runs.id']),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('assignment_warnings')
    op.drop_table('host_assignments')
    op.drop_table('pet_hosts')
    op.drop_table('assignment_runs')
    op.drop_table('app_users')
