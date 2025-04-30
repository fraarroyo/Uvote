from app import create_app
from models import User

def check_admin():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        if admin:
            print(f'Admin found:')
            print(f'Username: {admin.username}')
            print(f'Email: {admin.email}')
            print(f'Student ID: {admin.student_id}')
            print(f'Role: {admin.role}')
        else:
            print('No admin user found') 