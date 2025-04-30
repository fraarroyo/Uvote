"""add created_at to party_list

Revision ID: add_created_at_to_party_list
Revises: initial
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_created_at_to_party_list'
down_revision = 'initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add created_at column to party_list table
    op.add_column('party_list', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    # Set default value for existing records
    op.execute("UPDATE party_list SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    # Make the column non-nullable
    op.alter_column('party_list', 'created_at', nullable=False)


def downgrade():
    # Remove created_at column from party_list table
    op.drop_column('party_list', 'created_at') 