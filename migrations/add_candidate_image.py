from app import db
from app.models import Candidate

def upgrade():
    # Add image_path column to candidates table
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE candidate ADD COLUMN image_path VARCHAR(255)')
        conn.commit()

def downgrade():
    # Remove image_path column from candidates table
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE candidate DROP COLUMN image_path')
        conn.commit()

if __name__ == '__main__':
    upgrade() 