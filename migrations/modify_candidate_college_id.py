from app import app, db
from models import Candidate

def upgrade():
    with app.app_context():
        # Create a new table with nullable college_id
        db.engine.execute('''
            CREATE TABLE candidate_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                image_path VARCHAR(255),
                position_id INTEGER NOT NULL,
                college_id INTEGER,
                party_list VARCHAR(100),
                FOREIGN KEY (position_id) REFERENCES position (id),
                FOREIGN KEY (college_id) REFERENCES college (id)
            )
        ''')
        
        # Copy data from old table to new table
        db.engine.execute('''
            INSERT INTO candidate_new (id, name, description, image_path, position_id, college_id, party_list)
            SELECT id, name, description, image_path, position_id, college_id, party_list
            FROM candidate
        ''')
        
        # Drop the old table
        db.engine.execute('DROP TABLE candidate')
        
        # Rename the new table
        db.engine.execute('ALTER TABLE candidate_new RENAME TO candidate')
        
        db.session.commit()

def downgrade():
    with app.app_context():
        # Create a new table with NOT NULL college_id
        db.engine.execute('''
            CREATE TABLE candidate_old (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                image_path VARCHAR(255),
                position_id INTEGER NOT NULL,
                college_id INTEGER NOT NULL,
                party_list VARCHAR(100),
                FOREIGN KEY (position_id) REFERENCES position (id),
                FOREIGN KEY (college_id) REFERENCES college (id)
            )
        ''')
        
        # Copy data from current table to old table (this might fail if there are NULL college_ids)
        db.engine.execute('''
            INSERT INTO candidate_old (id, name, description, image_path, position_id, college_id, party_list)
            SELECT id, name, description, image_path, position_id, COALESCE(college_id, 1), party_list
            FROM candidate
        ''')
        
        # Drop the current table
        db.engine.execute('DROP TABLE candidate')
        
        # Rename the old table
        db.engine.execute('ALTER TABLE candidate_old RENAME TO candidate')
        
        db.session.commit() 