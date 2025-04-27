from app import create_app
from extensions import db
from app.routes import init_default_admin

application = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_default_admin()
    app.run(debug=True)
