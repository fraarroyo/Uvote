import pytest
import os
import tempfile
from io import BytesIO
from models import VoterList, EligibleStudent

def test_upload_voter_list(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # Create a test PDF file
    pdf_content = b'%PDF-1.4\n1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n3 0 obj\n<</Type /Page /Parent 2 0 R /Resources <<>> /Contents 4 0 R>>\nendobj\n4 0 obj\n<</Length 44>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000056 00000 n\n0000000102 00000 n\n0000000176 00000 n\ntrailer\n<</Size 5 /Root 1 0 R>>\nstartxref\n236\n%%EOF'
    
    # Create a test file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(pdf_content)
        temp_file.flush()
        
        # Upload the file
        with open(temp_file.name, 'rb') as f:
            response = client.post('/admin/voters/upload', data={
                'file': (f, 'test.pdf'),
                'college_id': init_database['college'].id
            }, follow_redirects=True)
    
    # Clean up
    os.unlink(temp_file.name)
    
    assert response.status_code == 200
    assert b'Voter list uploaded successfully' in response.data
    
    # Verify voter list was created
    voter_list = VoterList.query.filter_by(college_id=init_database['college'].id).first()
    assert voter_list is not None
    assert voter_list.filename == 'test.pdf'

def test_upload_invalid_file(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # Create a test text file (invalid format)
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b'Test content')
        temp_file.flush()
        
        # Upload the file
        with open(temp_file.name, 'rb') as f:
            response = client.post('/admin/voters/upload', data={
                'file': (f, 'test.txt'),
                'college_id': init_database['college'].id
            })
    
    # Clean up
    os.unlink(temp_file.name)
    
    assert response.status_code == 200
    assert b'Invalid file format' in response.data
    
    # Verify no voter list was created
    voter_list = VoterList.query.filter_by(college_id=init_database['college'].id).first()
    assert voter_list is None

def test_clear_voter_list(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # Create a test voter list
    voter_list = VoterList(
        filename='test.pdf',
        data=b'Test content',
        college_id=init_database['college'].id
    )
    db.session.add(voter_list)
    db.session.commit()
    
    # Clear the voter list
    response = client.get(f'/admin/voters/clear/{init_database["college"].id}', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Voter list cleared successfully' in response.data
    
    # Verify voter list was deleted
    voter_list = VoterList.query.filter_by(college_id=init_database['college'].id).first()
    assert voter_list is None

def test_import_eligible_students(client, init_database):
    # Login as admin
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    
    # Create a test CSV file
    csv_content = 'student_id,last_name,first_name,middle_name,email,course,year,section\n12345,Doe,John,,john@example.com,CS,3,A'
    csv_file = BytesIO(csv_content.encode())
    
    # Import the CSV
    response = client.post('/admin/users/import', data={
        'file': (csv_file, 'test.csv'),
        'college_id': init_database['college'].id
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Students imported successfully' in response.data
    
    # Verify student was imported
    student = EligibleStudent.query.filter_by(student_id='12345').first()
    assert student is not None
    assert student.email == 'john@example.com'
    assert student.college_id == init_database['college'].id 