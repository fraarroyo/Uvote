from app import app, db
from models import User

def upgrade():
    with app.app_context():
        # Create a new table with the desired structure
        db.engine.execute('''
            CREATE TABLE user_new (
                id INTEGER PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(128),
                student_id VARCHAR(20) UNIQUE NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'voter',
                college_id INTEGER NOT NULL,
                FOREIGN KEY (college_id) REFERENCES college (id)
            )
        ''')
        
        # Copy data from old table to new table
        db.engine.execute('''
            INSERT INTO user_new (id, username, email, password_hash, student_id, role, college_id)
            SELECT id, username, email, password_hash, student_id, role, 1
            FROM user
        ''')
        
        # Drop the old table
        db.engine.execute('DROP TABLE user')
        
        # Rename the new table
        db.engine.execute('ALTER TABLE user_new RENAME TO user')
        
        db.session.commit()

def downgrade():
    with app.app_context():
        # Create a new table without the college_id column
        db.engine.execute('''
            CREATE TABLE user_old (
                id INTEGER PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(128),
                student_id VARCHAR(20) UNIQUE NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'voter'
            )
        ''')
        
        # Copy data from current table to old table
        db.engine.execute('''
            INSERT INTO user_old (id, username, email, password_hash, student_id, role)
            SELECT id, username, email, password_hash, student_id, role
            FROM user
        ''')
        
        # Drop the current table
        db.engine.execute('DROP TABLE user')
        
        # Rename the old table
        db.engine.execute('ALTER TABLE user_old RENAME TO user')
        
        db.session.commit() 