"""add code and created_at to college

Revision ID: add_college_fields
Revises: add_college_columns
Create Date: 2024-04-25 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_college_fields'
down_revision = 'add_college_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Add code column
    op.add_column('college', sa.Column('code', sa.String(20), nullable=True))
    
    # Add created_at column
    op.add_column('college', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    # Update existing rows with default values
    op.execute("UPDATE college SET code = 'DEFAULT' WHERE code IS NULL")
    op.execute("UPDATE college SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    # Make the columns non-nullable after setting default values
    op.alter_column('college', 'code',
                    existing_type=sa.String(20),
                    nullable=False)
    op.alter_column('college', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False)
    
    # Add unique constraint to code
    op.create_unique_constraint('uq_college_code', 'college', ['code'])

def downgrade():
    op.drop_constraint('uq_college_code', 'college', type_='unique')
    op.drop_column('college', 'created_at')
    op.drop_column('college', 'code') 