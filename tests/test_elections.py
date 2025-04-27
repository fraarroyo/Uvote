import pytest
from flask import url_for
from models import Election, Position, Candidate, Vote
from datetime import datetime, timedelta

def test_create_election(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    response = client.post('/admin/election/create', data={
        'title': 'New Election',
        'description': 'Test Description',
        'start_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
        'end_date': (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'New Election' in response.data
    
    # Verify election was created
    election = Election.query.filter_by(title='New Election').first()
    assert election is not None
    assert election.description == 'Test Description'

def test_create_position(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    response = client.post('/admin/position/create', data={
        'title': 'New Position',
        'description': 'Test Description',
        'election_id': init_database['election'].id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'New Position' in response.data
    
    # Verify position was created
    position = Position.query.filter_by(title='New Position').first()
    assert position is not None
    assert position.election_id == init_database['election'].id

def test_create_candidate(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    response = client.post('/admin/candidate/create', data={
        'name': 'New Candidate',
        'description': 'Test Description',
        'position_id': init_database['position'].id,
        'college_id': init_database['college'].id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'New Candidate' in response.data
    
    # Verify candidate was created
    candidate = Candidate.query.filter_by(name='New Candidate').first()
    assert candidate is not None
    assert candidate.position_id == init_database['position'].id

def test_vote(client, init_database):
    # Login as voter
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    response = client.post(f'/election/{init_database["election"].id}/confirm', data={
        'candidate_id': init_database['candidate'].id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Vote recorded successfully' in response.data
    
    # Verify vote was recorded
    vote = Vote.query.filter_by(
        user_id=init_database['user'].id,
        candidate_id=init_database['candidate'].id,
        election_id=init_database['election'].id
    ).first()
    assert vote is not None

def test_double_vote(client, init_database):
    # Login as voter
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # First vote
    client.post(f'/election/{init_database["election"].id}/confirm', data={
        'candidate_id': init_database['candidate'].id
    })
    
    # Attempt second vote
    response = client.post(f'/election/{init_database["election"].id}/confirm', data={
        'candidate_id': init_database['candidate'].id
    })
    
    assert response.status_code == 200
    assert b'You have already voted in this election' in response.data
    
    # Verify only one vote was recorded
    votes = Vote.query.filter_by(
        user_id=init_database['user'].id,
        election_id=init_database['election'].id
    ).all()
    assert len(votes) == 1 