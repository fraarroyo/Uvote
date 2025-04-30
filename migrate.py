from app import app, db
from models import Candidate

def migrate():
    with app.app_context():
        # Add image_path column if it doesn't exist
        try:
            db.engine.execute('ALTER TABLE candidate ADD COLUMN image_path VARCHAR(255)')
            print("Successfully added image_path column to candidate table")
        except Exception as e:
            print(f"Column might already exist or there was an error: {str(e)}")

if __name__ == '__main__':
    migrate() 