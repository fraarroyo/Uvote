import pytest
from flask import url_for
from models import User

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_success(client, init_database):
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data

def test_login_failure(client, init_database):
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data

def test_logout(client, init_database):
    # Login first
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # Then logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

def test_register_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_register_success(client, init_database):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'newpass',
        'confirm_password': 'newpass',
        'student_id': '67890',
        'college_id': init_database['college'].id
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

    # Verify user was created
    user = User.query.filter_by(email='new@example.com').first()
    assert user is not None
    assert user.username == 'newuser'

def test_register_duplicate_email(client, init_database):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'test@example.com',  # Already exists
        'password': 'newpass',
        'confirm_password': 'newpass',
        'student_id': '67890',
        'college_id': init_database['college'].id
    })
    assert response.status_code == 200
    assert b'Email already registered' in response.data

def test_register_duplicate_student_id(client, init_database):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'newpass',
        'confirm_password': 'newpass',
        'student_id': '12345',  # Already exists
        'college_id': init_database['college'].id
    })
    assert response.status_code == 200
    assert b'Student ID already registered' in response.data 