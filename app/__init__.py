# This file makes the app directory a Python package 

from flask import Flask, make_response
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
import os
from config import Config
from extensions import db, login_manager
from flask_login import LoginManager

csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config_class)

    # Configure upload paths
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.config['CANDIDATE_IMAGES'] = os.path.join(app.config['UPLOAD_FOLDER'], 'images', 'candidates')
    app.config['PARTY_IMAGES'] = os.path.join(app.config['UPLOAD_FOLDER'], 'party_images')
    
    # Create upload directories if they don't exist
    for directory in [app.config['UPLOAD_FOLDER'], 
                     app.config['CANDIDATE_IMAGES'], 
                     app.config['PARTY_IMAGES']]:
        try:
            os.makedirs(directory, exist_ok=True)
            # Ensure directory has correct permissions
            os.chmod(directory, 0o755)
        except Exception as e:
            app.logger.error(f"Error creating directory {directory}: {str(e)}")

    # Initialize CSRF protection
    csrf.init_app(app)

    # Make csrf_token available in templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token_value=generate_csrf())

    # Configure security headers
    @app.after_request
    def add_security_headers(response):
        # Content Security Policy
        csp = {
            'default-src': ["'self'", "https:", "http:"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'",
                "https://cdn.jsdelivr.net",
                "https://code.jquery.com",
                "https://cdnjs.cloudflare.com",
                "https://cdn.js.cloudflare.com",
                "*.pythonanywhere.com"
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://fonts.googleapis.com",
                "https://cdn.js.cloudflare.com",
                "*.pythonanywhere.com"
            ],
            'style-src-elem': [
                "'self'",
                "'unsafe-inline'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://fonts.googleapis.com",
                "https://cdn.js.cloudflare.com",
                "*.pythonanywhere.com"
            ],
            'font-src': [
                "'self'",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://fonts.gstatic.com",
                "https://fonts.googleapis.com",
                "data:",
                "*.pythonanywhere.com"
            ],
            'img-src': ["'self'", "data:", "https:", "blob:", "*.pythonanywhere.com"],
            'connect-src': ["'self'", "https:", "*.pythonanywhere.com"],
            'frame-src': ["'self'", "https:", "*.pythonanywhere.com"],
            'media-src': ["'self'", "https:", "*.pythonanywhere.com"],
            'object-src': ["'none'"]
        }
        
        # Convert CSP dict to string
        csp_string = '; '.join([
            f"{key} {' '.join(values)}"
            for key, values in csp.items()
        ])
        
        # Add security headers
        response.headers['Content-Security-Policy'] = csp_string
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response

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
    migrate = Migrate(app, db)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'main.login'  # Updated to use blueprint route
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

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