from app import app
from extensions import db

def upgrade():
    with app.app_context():
        # Add registration_date column to eligible_student table
        db.engine.execute('''
            ALTER TABLE eligible_student
            ADD COLUMN registration_date DATETIME
        ''')

def downgrade():
    with app.app_context():
        # Remove registration_date column from eligible_student table
        db.engine.execute('''
            ALTER TABLE eligible_student
            DROP COLUMN registration_date
        ''') 