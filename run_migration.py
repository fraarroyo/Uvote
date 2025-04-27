from app import app, db
from flask_migrate import Migrate, upgrade

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Run the migration
with app.app_context():
    upgrade() 