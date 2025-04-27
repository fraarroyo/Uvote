from app import create_app
from extensions import db
from models import College, User, Position, Candidate, Vote, PartyList, Platform, VoterList
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()

        # Add default colleges if they don't exist
        colleges = [
            College(name='BUHI CAMPUS', description='Buhi Campus'),
            College(name='CCS', description='College of Computer Studies'),
            College(name='CEA', description='College of Engineering and Architecture'),
            College(name='CAS', description='College of Arts and Sciences'),
            College(name='CTDE', description='College of Technology and Distance Education'),
            College(name='CTHBM', description='College of Tourism, Hospitality and Business Management'),
            College(name='CHS', description='College of Health Sciences')
        ]
        
        for college in colleges:
            existing = College.query.filter_by(name=college.name).first()
            if not existing:
                db.session.add(college)
        
        try:
            db.session.commit()
            print("Successfully added default colleges")
        except Exception as e:
            print(f"Error adding colleges: {str(e)}")
            db.session.rollback()

        # Add any missing columns
        try:
            # Add registration_date to eligible_student
            db.session.execute(text('''
                ALTER TABLE eligible_student
                ADD COLUMN registration_date DATETIME
            '''))
        except Exception as e:
            print(f"Note: registration_date column might already exist: {str(e)}")

        try:
            # Add party_list_id to candidate
            db.session.execute(text('''
                ALTER TABLE candidate
                ADD COLUMN party_list_id INTEGER
                REFERENCES party_list (id)
            '''))
        except Exception as e:
            print(f"Note: party_list_id column might already exist: {str(e)}")

        try:
            # Add college_id to candidate
            db.session.execute(text('''
                ALTER TABLE candidate
                ADD COLUMN college_id INTEGER
                REFERENCES college (id)
            '''))
        except Exception as e:
            print(f"Note: college_id column might already exist: {str(e)}")

        try:
            # Add image_path to candidate
            db.session.execute(text('''
                ALTER TABLE candidate
                ADD COLUMN image_path VARCHAR(255)
            '''))
        except Exception as e:
            print(f"Note: image_path column might already exist: {str(e)}")

        try:
            # Add created_at to candidate
            db.session.execute(text('''
                ALTER TABLE candidate
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            '''))
        except Exception as e:
            print(f"Note: created_at column might already exist: {str(e)}")

        print("Migration completed successfully") 