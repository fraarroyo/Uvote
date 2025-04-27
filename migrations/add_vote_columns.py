import os
import sqlite3

def upgrade():
    db_path = os.path.join('instance', 'uvote.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Disable foreign key constraint temporarily
        cursor.execute('PRAGMA foreign_keys=OFF')
        
        # Create new table with updated schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vote_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                candidate_id INTEGER,
                election_id INTEGER NOT NULL,
                position_id INTEGER NOT NULL,
                is_abstain BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (candidate_id) REFERENCES candidate (id),
                FOREIGN KEY (election_id) REFERENCES election (id),
                FOREIGN KEY (position_id) REFERENCES position (id)
            )
        ''')
        
        # Copy existing data if the old table exists
        try:
            cursor.execute('''
                INSERT INTO vote_new (id, user_id, candidate_id, election_id, timestamp)
                SELECT id, user_id, candidate_id, election_id, timestamp
                FROM vote
            ''')
        except sqlite3.Error as e:
            print("No existing data to migrate:", str(e))
        
        # Drop the old table
        cursor.execute('DROP TABLE IF EXISTS vote')
        
        # Rename the new table
        cursor.execute('ALTER TABLE vote_new RENAME TO vote')
        
        # Re-enable foreign key constraint
        cursor.execute('PRAGMA foreign_keys=ON')
        
        conn.commit()
        print("Successfully updated vote table schema")
        
    except Exception as e:
        print("Error updating table:", str(e))
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    upgrade() 