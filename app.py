from app import create_app
from extensions import db
from app.routes import init_default_admin
from app.models import College
import os

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            print("Dropped all tables successfully")
            
            # Recreate all tables
            db.create_all()
            print("Created all tables successfully")
            
            # Create default college if it doesn't exist
            default_college = College.query.filter_by(name='Default College').first()
            if not default_college:
                default_college = College(name='Default College')
                db.session.add(default_college)
                db.session.commit()
                print("Created default college")
            
            # Create default admin
            init_default_admin(default_college.id)
            print("Created default admin user")
            
            print("Database initialization completed successfully")
        except Exception as e:
            print(f"Error during database initialization: {str(e)}")
            raise
            
    app.run(debug=True)

