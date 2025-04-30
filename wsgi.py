import sys
import os

# Add your project directory to the sys.path
path = '/home/Francis17/Uvote'
if path not in sys.path:
    sys.path.append(path)

# Import your app
from app import create_app
application = create_app()

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Configure static files
application.config['UPLOAD_FOLDER'] = os.path.join(application.root_path, 'static')
application.config['CANDIDATE_IMAGES'] = os.path.join(application.config['UPLOAD_FOLDER'], 'images', 'candidates')
application.config['PARTY_IMAGES'] = os.path.join(application.config['UPLOAD_FOLDER'], 'party_images')

# Create upload directories
os.makedirs(application.config['CANDIDATE_IMAGES'], exist_ok=True)
os.makedirs(application.config['PARTY_IMAGES'], exist_ok=True)

if __name__ == '__main__':
    application.run()