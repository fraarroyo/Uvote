import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def migrate_candidates():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uvote.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Add created_at column if it doesn't exist
            db.session.execute(text('''
                ALTER TABLE candidate 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            '''))
            print("Successfully added created_at column to candidate table")
        except Exception as e:
            print(f"Note: created_at column might already exist: {str(e)}")

        try:
            # Add party_list_id column if it doesn't exist
            db.session.execute(text('''
                ALTER TABLE candidate 
                ADD COLUMN party_list_id INTEGER 
                REFERENCES party_list (id)
            '''))
            print("Successfully added party_list_id column to candidate table")
        except Exception as e:
            print(f"Note: party_list_id column might already exist: {str(e)}")

        # Commit the changes
        db.session.commit()
        print("Migration completed successfully")

if __name__ == '__main__':
    migrate_candidates() 