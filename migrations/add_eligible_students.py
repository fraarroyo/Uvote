from app import app
from extensions import db

def upgrade():
    with app.app_context():
        # Create the eligible_student table
        db.engine.execute('''
            CREATE TABLE eligible_student (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(20) NOT NULL UNIQUE,
                last_name VARCHAR(100) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                email VARCHAR(120) NOT NULL UNIQUE,
                course VARCHAR(50),
                year VARCHAR(10),
                section VARCHAR(20),
                college_id INTEGER NOT NULL,
                is_registered BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (college_id) REFERENCES college (id)
            )
        ''')

def downgrade():
    with app.app_context():
        # Drop the eligible_student table
        db.engine.execute('DROP TABLE IF EXISTS eligible_student') 