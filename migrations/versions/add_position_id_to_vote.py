"""add position_id to vote

Revision ID: add_position_id_to_vote
Revises: update_candidates_table
Create Date: 2024-04-27 05:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_position_id_to_vote'
down_revision = 'update_candidates_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add position_id column
    op.add_column('vote', sa.Column('position_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_vote_position',
        'vote', 'position',
        ['position_id'], ['id']
    )
    
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
    # Remove foreign key constraint
    op.drop_constraint('fk_vote_position', 'vote', type_='foreignkey')
    
    # Remove position_id column
    op.drop_column('vote', 'position_id') 