"""add vote columns

Revision ID: add_vote_columns
Revises: update_candidates_table
Create Date: 2024-04-27 05:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_vote_columns'
down_revision = 'update_candidates_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add position_id column
    op.add_column('vote', sa.Column('position_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_vote_position', 'vote', 'position', ['position_id'], ['id'])
    
    # Add is_abstain column
    op.add_column('vote', sa.Column('is_abstain', sa.Boolean(), nullable=True, server_default='false'))
    
    # Update existing votes to have position_id
    op.execute("""
        UPDATE vote 
        SET position_id = (
            SELECT position_id 
            FROM candidate 
            WHERE candidate.id = vote.candidate_id
        )
        WHERE candidate_id IS NOT NULL
    """)
    
    # Make position_id non-nullable after updating existing records
    op.alter_column('vote', 'position_id', nullable=False)

def downgrade():
    # Remove is_abstain column
    op.drop_column('vote', 'is_abstain')
    
    # Remove position_id column
    op.drop_constraint('fk_vote_position', 'vote', type_='foreignkey')
    op.drop_column('vote', 'position_id') 