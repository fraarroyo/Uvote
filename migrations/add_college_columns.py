from app import app, db
from models import User, Candidate

def upgrade():
    with app.app_context():
        # Add college column to User table
        db.engine.execute('ALTER TABLE user ADD COLUMN college VARCHAR(100)')
        
        # Add college column to Candidate table
        db.engine.execute('ALTER TABLE candidate ADD COLUMN college VARCHAR(100)')
        
        # Set default college for existing users
        db.engine.execute("UPDATE user SET college = 'College of Engineering' WHERE college IS NULL")
        
        # Set default college for existing candidates
        db.engine.execute("UPDATE candidate SET college = 'College of Engineering' WHERE college IS NULL")
        
        db.session.commit()

def downgrade():
    with app.app_context():
        # Remove college column from User table
        db.engine.execute('ALTER TABLE user DROP COLUMN college')
        
        # Remove college column from Candidate table
        db.engine.execute('ALTER TABLE candidate DROP COLUMN college')
        
        db.session.commit()

if __name__ == '__main__':
    upgrade() 