from app import db
from app.models import User

def upgrade():
    # Add role column
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT "voter"')
        
        # Update existing admin users
        conn.execute('UPDATE user SET role = "admin" WHERE is_admin = 1')
        
    db.session.commit()

def downgrade():
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE user DROP COLUMN role')
    
    db.session.commit()

if __name__ == '__main__':
    upgrade() 