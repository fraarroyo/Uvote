from app import app, db
from models import Candidate, College

def upgrade():
    with app.app_context():
        # Create a new table with the desired structure
        db.engine.execute('''
            CREATE TABLE candidate_new (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                image_path VARCHAR(255),
                position_id INTEGER NOT NULL,
                college_id INTEGER NOT NULL,
                FOREIGN KEY (position_id) REFERENCES position (id),
                FOREIGN KEY (college_id) REFERENCES college (id)
            )
        ''')
        
        # Get default college
        default_college = College.query.first()
        if not default_college:
            # Create default college if none exists
            default_college = College(name='College of Engineering', description='Default College')
            db.session.add(default_college)
            db.session.flush()
        
        # Copy data from old table to new table
        db.engine.execute(f'''
            INSERT INTO candidate_new (id, name, description, image_path, position_id, college_id)
            SELECT id, name, description, image_path, position_id, {default_college.id}
            FROM candidate
        ''')
        
        # Drop the old table
        db.engine.execute('DROP TABLE candidate')
        
        # Rename the new table
        db.engine.execute('ALTER TABLE candidate_new RENAME TO candidate')
        
        db.session.commit()

def downgrade():
    with app.app_context():
        # Create a new table without the college_id column
        db.engine.execute('''
            CREATE TABLE candidate_old (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                image_path VARCHAR(255),
                position_id INTEGER NOT NULL,
                FOREIGN KEY (position_id) REFERENCES position (id)
            )
        ''')
        
        # Copy data from current table to old table
        db.engine.execute('''
            INSERT INTO candidate_old (id, name, description, image_path, position_id)
            SELECT id, name, description, image_path, position_id
            FROM candidate
        ''')
        
        # Drop the current table
        db.engine.execute('DROP TABLE candidate')
        
        # Rename the old table
        db.engine.execute('ALTER TABLE candidate_old RENAME TO candidate')
        
        db.session.commit() 