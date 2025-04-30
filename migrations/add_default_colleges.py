from app import app, db
from models import College

def upgrade():
    with app.app_context():
        # Define the colleges
        colleges = [
            College(name='BUHI CAMPUS', description='Buhi Campus'),
            College(name='CCS', description='College of Computer Studies'),
            College(name='CEA', description='College of Engineering and Architecture'),
            College(name='CAS', description='College of Arts and Sciences'),
            College(name='CTDE', description='College of Technology and Distance Education'),
            College(name='CTHBM', description='College of Tourism, Hospitality and Business Management'),
            College(name='CHS', description='College of Health Sciences')
        ]
        
        # Add all colleges
        for college in colleges:
            existing = College.query.filter_by(name=college.name).first()
            if not existing:
                db.session.add(college)
        
        db.session.commit()

def downgrade():
    with app.app_context():
        # Remove the colleges
        College.query.filter(College.name.in_([
            'BUHI CAMPUS', 'CCS', 'CEA', 'CAS', 'CTDE', 'CTHBM', 'CHS'
        ])).delete()
        db.session.commit() 