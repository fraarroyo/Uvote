from app import app
import os

# Set the static folder to the app/static directory
app.static_folder = os.path.join('app', 'static')
app.static_url_path = '/static' 