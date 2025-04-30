import sys
import os

# Add current directory to sys.path to prioritize app.py import over app directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import app

def migrate():
    with app.app.app_context():
        try:
            app.db.engine.execute('ALTER TABLE candidate ADD COLUMN party_list_id INTEGER')
            print("Successfully added party_list_id column to candidate table")
        except Exception as e:
            print(f"Column might already exist or there was an error: {str(e)}")

if __name__ == '__main__':
    migrate()
