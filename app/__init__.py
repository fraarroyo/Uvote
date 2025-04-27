# This file makes the app directory a Python package 

from flask import Flask, session
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

    # Make csrf_token available in all responses
    @app.after_request
    def add_csrf_token_cookie(response):
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf()
        response.set_cookie('csrf_token', session['csrf_token'])
        return response

    # Make csrf_token available in templates
    @app.context_processor
    def inject_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf()
        return dict(csrf_token_value=session['csrf_token'])

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

    # Import models for user_loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app 