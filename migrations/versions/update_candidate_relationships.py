"""update candidate relationships

Revision ID: update_candidate_rel
Revises: modify_candidate_college_id
Create Date: 2024-03-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_candidate_rel'
down_revision = 'modify_candidate_college_id'
branch_labels = None
depends_on = None

def upgrade():
    # Make party_list_id not nullable
    op.alter_column('candidate', 'party_list_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Add unique constraint
    op.create_unique_constraint(
        'unique_candidate_per_position',
        'candidate',
        ['name', 'position_id']
    )

def downgrade():
    # Remove unique constraint
    op.drop_constraint(
        'unique_candidate_per_position',
        'candidate',
        type_='unique'
    )
    
    # Make party_list_id nullable again
    op.alter_column('candidate', 'party_list_id',
                    existing_type=sa.Integer(),
                    nullable=True) 