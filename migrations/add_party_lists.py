import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def upgrade():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uvote.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    
    with app.app_context():
        # Create party_list table
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS party_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                image_path VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        
        # Create platform table
        db.session.execute(text('''
            CREATE TABLE IF NOT EXISTS platform (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                party_list_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (party_list_id) REFERENCES party_list (id)
            )
        '''))
        
        # Add party_list_id column to candidate table if it doesn't exist
        try:
            db.session.execute(text('''
                ALTER TABLE candidate ADD COLUMN party_list_id INTEGER
                REFERENCES party_list (id)
            '''))
        except Exception as e:
            print("Column party_list_id might already exist:", str(e))
        
        db.session.commit()
        print("Successfully created party_list and platform tables")

if __name__ == '__main__':
    upgrade() 