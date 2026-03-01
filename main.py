from app import app  # noqa: F401
from flask import Flask
app=Flask(__name__)
def init_db():
    with app.app_context():
        db.create_all()
        with app.app_context():
            try:
                from models import User
                if not User.query.filter_by(username='admin').first():
                    create_user("admin", "admin@admin.com", "admin", role='admin')
            except Exception as e:
                app.logger.error(f"Error creating admin user: {e}")


# Create admin user if it doesn't exist

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
