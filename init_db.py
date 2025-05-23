import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db

def init_db():
    app = create_app()
    
    with app.app_context():
        # Import models here to avoid circular imports
        from app.models import College, User, Election, Position, Candidate, PartyList, Platform
        
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        # Create test college
        college = College(name='Test College')
        db.session.add(college)
        db.session.commit()

        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            student_id='00000',
            role='admin',
            college_id=college.id
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

        # Create test election
        election = Election(
            title='Test Election',
            description='Test Description',
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=7),
            is_active=True
        )
        db.session.add(election)
        db.session.commit()

        # Create test position
        position = Position(
            title='Test Position',
            description='Test Description',
            election_id=election.id
        )
        db.session.add(position)
        db.session.commit()

        # Create test party list
        party_list = PartyList(
            name='Test Party',
            description='Test Description'
        )
        db.session.add(party_list)
        db.session.commit()

        # Create test platform
        platform = Platform(
            title='Test Platform',
            description='Test Description',
            party_list_id=party_list.id
        )
        db.session.add(platform)
        db.session.commit()

        # Create test candidate
        candidate = Candidate(
            name='Test Candidate',
            description='Test Description',
            position_id=position.id,
            college_id=college.id,
            party_list_id=party_list.id
        )
        db.session.add(candidate)
        db.session.commit()

        print('Database initialized successfully!')

if __name__ == '__main__':
    from datetime import datetime, timedelta
    init_db()