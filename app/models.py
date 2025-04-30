from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), default='voter')  # 'admin' or 'voter'
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    is_default_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    college = db.relationship('College', back_populates='users')
    votes = db.relationship('Vote', back_populates='user')
    audit_logs = db.relationship('AuditLog', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @classmethod
    def create_default_admin(cls, college_id):
        """Create the default admin user if it doesn't exist."""
        default_admin = cls.query.filter_by(is_default_admin=True).first()
        if not default_admin:
            admin = cls(
                username='admin',
                email='admin@uvote.com',
                student_id='ADMIN001',
                role='admin',
                college_id=college_id,
                is_default_admin=True
            )
            admin.set_password('admin123')  # Set a default password
            db.session.add(admin)
            db.session.commit()
            return admin
        return default_admin

class College(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    # Relationships
    users = db.relationship('User', back_populates='college')
    eligible_students = db.relationship('EligibleStudent', back_populates='college')
    voter_lists = db.relationship('VoterList', back_populates='college')
    candidates = db.relationship('Candidate', back_populates='college')
    user_lists = db.relationship('UserList', back_populates='college')

class EligibleStudent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    course = db.Column(db.String(50))
    year = db.Column(db.String(10))
    section = db.Column(db.String(20))
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    is_registered = db.Column(db.Boolean, default=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    college = db.relationship('College', back_populates='eligible_students')

class VoterList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    
    # Relationships
    college = db.relationship('College', back_populates='voter_lists')

    def __repr__(self):
        return f'<VoterList {self.filename}>'

class PartyList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    platforms = db.relationship('Platform', back_populates='party_list', lazy=True)
    candidates = db.relationship('Candidate', back_populates='party_list', lazy=True)

    def __repr__(self):
        return f'<PartyList {self.name}>'

class Platform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    party_list_id = db.Column(db.Integer, db.ForeignKey('party_list.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    party_list = db.relationship('PartyList', back_populates='platforms')

    def __repr__(self):
        return f'<Platform {self.title}>'

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    positions = db.relationship('Position', back_populates='election', lazy=True, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='election', cascade='all, delete-orphan')

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    election = db.relationship('Election', back_populates='positions')
    candidates = db.relationship('Candidate', back_populates='position', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', back_populates='position', cascade='all, delete-orphan')

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    party_list_id = db.Column(db.Integer, db.ForeignKey('party_list.id'))
    position_id = db.Column(db.Integer, db.ForeignKey('position.id', ondelete='CASCADE'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'))
    image_path = db.Column(db.String(255))
    
    # Relationships
    party_list = db.relationship('PartyList', back_populates='candidates')
    position = db.relationship('Position', back_populates='candidates')
    college = db.relationship('College', back_populates='candidates')
    votes = db.relationship('Vote', back_populates='candidate', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Candidate {self.name}>'

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id', ondelete='CASCADE'), nullable=True)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id', ondelete='CASCADE'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('position.id', ondelete='CASCADE'), nullable=False)
    is_abstain = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='votes')
    candidate = db.relationship('Candidate', back_populates='votes')
    position = db.relationship('Position', back_populates='votes')

    def __repr__(self):
        return f'<Vote {self.id}>'

class StudentNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    user_list_id = db.Column(db.Integer, db.ForeignKey('user_list.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user_list = db.relationship('UserList', back_populates='student_numbers')

class UserList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    college = db.relationship('College', back_populates='user_lists')
    student_numbers = db.relationship('StudentNumber', back_populates='user_list')
    
    def check_student_number(self, student_number):
        """Check if a student number exists in this user list."""
        return StudentNumber.query.filter_by(
            user_list_id=self.id,
            student_id=student_number.strip()
        ).first() is not None

    def __repr__(self):
        return f'<UserList {self.filename}>'

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    
    # Relationships
    user = db.relationship('User', back_populates='audit_logs')
    election = db.relationship('Election', back_populates='audit_logs')