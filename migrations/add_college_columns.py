"""add college columns

Revision ID: add_college_columns
Revises: 
Create Date: 2024-04-24 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_college_columns'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add code column to College table
    op.add_column('college', sa.Column('code', sa.String(10), nullable=True))
    
    # Update existing colleges with default codes
    op.execute("""
        UPDATE college 
        SET code = CASE 
            WHEN name = 'BUHI CAMPUS' THEN 'BC'
            WHEN name = 'CCS' THEN 'CCS'
            WHEN name = 'CEA' THEN 'CEA'
            WHEN name = 'CAS' THEN 'CAS'
            WHEN name = 'CTDE' THEN 'CTDE'
            WHEN name = 'CTHBM' THEN 'CTHBM'
            WHEN name = 'CHS' THEN 'CHS'
            ELSE SUBSTRING(name, 1, 3)
        END
        WHERE code IS NULL
    """)
    
    # Make code column non-nullable
    op.alter_column('college', 'code', nullable=False)
    
    # Add unique constraint to code
    op.create_unique_constraint('uq_college_code', 'college', ['code'])
    
    # Add college column to User table
    op.add_column('user', sa.Column('college', sa.String(100), nullable=True))
    
    # Add college column to Candidate table
    op.add_column('candidate', sa.Column('college', sa.String(100), nullable=True))
    
    # Set default college for existing users
    op.execute("UPDATE user SET college = 'College of Engineering' WHERE college IS NULL")
    
    # Set default college for existing candidates
    op.execute("UPDATE candidate SET college = 'College of Engineering' WHERE college IS NULL")
    
    # Make college columns non-nullable
    op.alter_column('user', 'college', nullable=False)
    op.alter_column('candidate', 'college', nullable=False)

def downgrade():
    # Remove college column from User table
    op.drop_column('user', 'college')
    
    # Remove college column from Candidate table
    op.drop_column('candidate', 'college')
    
    # Remove unique constraint from college code
    op.drop_constraint('uq_college_code', 'college', type_='unique')
    
    # Remove code column from College table
    op.drop_column('college', 'code')