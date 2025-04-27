"""add created_at to college

Revision ID: add_college_created_at
Revises: add_college_columns
Create Date: 2024-04-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_college_created_at'
down_revision = 'add_college_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Add created_at column with default value
    op.add_column('college', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    # Update existing rows with current timestamp
    op.execute("UPDATE college SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    # Make the column non-nullable after setting default values
    op.alter_column('college', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False)

def downgrade():
    op.drop_column('college', 'created_at') 