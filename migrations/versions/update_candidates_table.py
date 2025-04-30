"""update candidates table

Revision ID: update_candidates_table
Revises: add_created_at_to_party_list
Create Date: 2024-03-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'update_candidates_table'
down_revision = 'add_created_at_to_party_list'
branch_labels = None
depends_on = None


def upgrade():
    # Add created_at column to candidates table if it doesn't exist
    op.add_column('candidate', sa.Column('created_at', sa.DateTime(), nullable=True))
    
    # Set default value for existing records
    op.execute("UPDATE candidate SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    # Make the column non-nullable
    op.alter_column('candidate', 'created_at', nullable=False)

    # Add party_list_id column if it doesn't exist
    # Using try-except because the column might already exist from previous migrations
    try:
        op.add_column('candidate', sa.Column('party_list_id', sa.Integer(), nullable=True))
        op.create_foreign_key(
            'fk_candidate_party_list',
            'candidate', 'party_list',
            ['party_list_id'], ['id']
        )
    except Exception as e:
        print(f"Note: party_list_id column might already exist: {e}")


def downgrade():
    # Remove foreign key constraint first
    try:
        op.drop_constraint('fk_candidate_party_list', 'candidate', type_='foreignkey')
    except Exception:
        pass  # Constraint might not exist
    
    # Remove columns
    try:
        op.drop_column('candidate', 'party_list_id')
    except Exception:
        pass  # Column might not exist
    
    op.drop_column('candidate', 'created_at') 