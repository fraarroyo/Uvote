import pytest
from app import app, db
from models import User, College, Election, Position, Candidate
import os
import tempfile
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def init_database():
    # Create test college
    college = College(name='Test College', description='Test Description')
    db.session.add(college)
    db.session.commit()

    # Create test user
    user = User(
        username='testuser',
        email='test@example.com',
        student_id='12345',
        role='voter',
        college_id=college.id
    )
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()

    # Create test election
    election = Election(
        title='Test Election',
        description='Test Description',
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1),
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

    # Create test candidate
    candidate = Candidate(
        name='Test Candidate',
        description='Test Description',
        position_id=position.id,
        college_id=college.id
    )
    db.session.add(candidate)
    db.session.commit()

    return {
        'college': college,
        'user': user,
        'election': election,
        'position': position,
        'candidate': candidate
    } 