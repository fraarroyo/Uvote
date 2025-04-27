import os
import sys
from flask import Flask
from extensions import db, login_manager
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import User, College

# Create Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uvote.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Import models
from app.models import User, College

def create_admin():
    app = create_app()
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if admin user already exists
        admin = User.query.filter_by(role='admin').first()
        if admin:
            print('Admin user already exists.')
            return
        
        # Check if test college exists
        college = College.query.filter_by(name='Test College').first()
        if not college:
            # Create test college
            college = College(name='Test College')
            db.session.add(college)
            try:
                db.session.commit()
                print('Created test college.')
            except Exception as e:
                print(f'Error creating college: {str(e)}')
                db.session.rollback()
                return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            student_id='00000',
            role='admin',
            college_id=college.id
        )
        admin.set_password('admin123')
        
        try:
            db.session.add(admin)
            db.session.commit()
            print('Admin user created successfully!')
            print('Username: admin')
            print('Password: admin123')
        except Exception as e:
            print(f'Error creating admin: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    create_admin() 