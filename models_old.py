from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from datetime import datetime
from typing import Optional, List

class College(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    users = db.relationship('User', backref='college_ref', lazy=True)
    candidates = db.relationship('Candidate', backref='college_ref', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='voter')  # 'admin' or 'voter'
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    votes = db.relationship('Vote', backref='voter', lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

class Election(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    positions = db.relationship('Position', backref='election', lazy=True)

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    candidates = db.relationship('Candidate', backref='position', lazy=True)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))  # Path to store the image
    position_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=True)  # Allow null for non-representative positions
    party_list_id = db.Column(db.Integer, db.ForeignKey('party_list.id'), nullable=True)
    votes = db.relationship('Vote', backref='candidate', lazy=True)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    election_id = db.Column(db.Integer, db.ForeignKey('election.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
    registration_date = db.Column(db.DateTime, nullable=True)
    
    college = db.relationship('College', backref='eligible_students')

    def __repr__(self):
        return f'<EligibleStudent {self.student_id}>'

class VoterList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    college = db.relationship('College', backref='voter_lists')

class PartyList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    platforms = db.relationship('Platform', backref='party_list', lazy=True)
    candidates = db.relationship('Candidate', backref='party_list_ref', lazy=True)

class Platform(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    party_list_id = db.Column(db.Integer, db.ForeignKey('party_list.id'), nullable=False)

class UserList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    college = db.relationship('College', backref=db.backref('user_lists', lazy=True))
    student_numbers = db.relationship('StudentNumber', backref='user_list', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<UserList {self.filename}>'

class StudentNumber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    user_list_id = db.Column(db.Integer, db.ForeignKey('user_list.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add a unique constraint to prevent duplicate student numbers in the same list
    __table_args__ = (db.UniqueConstraint('student_id', 'user_list_id', name='uix_student_id_user_list'),) 