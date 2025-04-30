"""initial migration

Revision ID: initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create College table
    op.create_table('college',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create User table
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=True),
        sa.Column('student_id', sa.String(length=20), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['college_id'], ['college.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('student_id'),
        sa.UniqueConstraint('username')
    )

    # Create Election table
    op.create_table('election',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Position table
    op.create_table('position',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('election_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['election_id'], ['election.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Candidate table
    op.create_table('candidate',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=255), nullable=True),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('college_id', sa.Integer(), nullable=True),
        sa.Column('party_list_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['college.id'], ),
        sa.ForeignKeyConstraint(['party_list_id'], ['party_list.id'], ),
        sa.ForeignKeyConstraint(['position_id'], ['position.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Vote table
    op.create_table('vote',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('election_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate.id'], ),
        sa.ForeignKeyConstraint(['election_id'], ['election.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create EligibleStudent table
    op.create_table('eligible_student',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.String(length=20), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('course', sa.String(length=50), nullable=True),
        sa.Column('year', sa.String(length=10), nullable=True),
        sa.Column('section', sa.String(length=20), nullable=True),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.Column('is_registered', sa.Boolean(), nullable=True),
        sa.Column('registration_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['college_id'], ['college.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('student_id')
    )

    # Create VoterList table
    op.create_table('voter_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('college_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['college_id'], ['college.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create PartyList table
    op.create_table('party_list',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Platform table
    op.create_table('platform',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('party_list_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['party_list_id'], ['party_list.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('platform')
    op.drop_table('party_list')
    op.drop_table('voter_list')
    op.drop_table('eligible_student')
    op.drop_table('vote')
    op.drop_table('candidate')
    op.drop_table('position')
    op.drop_table('election')
    op.drop_table('user')
    op.drop_table('college') 