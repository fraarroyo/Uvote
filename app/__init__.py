# This file makes the app directory a Python package 

from flask import Flask
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
import os
from config import Config
from extensions import db, login_manager

csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Make csrf_token available in templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token_value=generate_csrf())

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Add custom datetime filter
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ""
        return value.strftime(format)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'main.login'  # Updated to use blueprint route
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Import models
    from app.models import (
        User, College, EligibleStudent, VoterList, PartyList,
        Platform, Election, Position, Candidate, Vote,
        StudentNumber, UserList, AuditLog
    )

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default college if it doesn't exist
        if not College.query.first():
            default_college = College(name='Default College')
            db.session.add(default_college)
            db.session.commit()
            # Create default admin user
            User.create_default_admin(default_college.id)

    return app

# Create the application instance
app = create_app()

# Make both create_app and app available for import
__all__ = ['create_app', 'app'] 