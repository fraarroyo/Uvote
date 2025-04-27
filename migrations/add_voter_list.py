from app import create_app, db
from app.models import VoterList

def upgrade():
    app = create_app()
    with app.app_context():
        db.create_all()

def downgrade():
    app = create_app()
    with app.app_context():
        VoterList.__table__.drop(db.engine)

if __name__ == '__main__':
    upgrade()
    print("Successfully created voter_list table") 