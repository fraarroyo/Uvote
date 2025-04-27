from app import app, db
from models import Candidate

def upgrade():
    with app.app_context():
        # Add party_list_id column to Candidate table
        db.engine.execute('ALTER TABLE candidate ADD COLUMN party_list_id INTEGER')
        db.engine.execute('PRAGMA foreign_keys=off;')
        # SQLite does not support adding foreign key constraints via ALTER TABLE, so this is a workaround
        # Normally, you would recreate the table with the foreign key constraint
        db.engine.execute('PRAGMA foreign_keys=on;')
        db.session.commit()

def downgrade():
    with app.app_context():
        # Remove party_list_id column from Candidate table
        # SQLite does not support DROP COLUMN, so this is a placeholder
        # You may need to recreate the table without this column for a full downgrade
        pass
        db.session.commit()
