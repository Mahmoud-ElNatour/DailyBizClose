import os
import hashlib

from app import app
from models import db, User

def ensure_admin(username="admin", password="admin", email="admin@admin.com"):
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"Admin user already exists: {username}")
            return

        user = User(
            username=username,
            email=email,
            password_hash=hashlib.sha256(password.encode()).hexdigest(),
            role="admin",
        )
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user: {username}")

if __name__ == "__main__":
    # optional: create tables if they don't exist
    with app.app_context():
        db.create_all()

    # You can override via env vars if you want:
    # set ADMIN_USERNAME=admin
    # set ADMIN_PASSWORD=admin
    # set ADMIN_EMAIL=admin@admin.com
    ensure_admin(
        username=os.getenv("ADMIN_USERNAME", "admin"),
        password=os.getenv("ADMIN_PASSWORD", "admin"),
        email=os.getenv("ADMIN_EMAIL", "admin@admin.com"),
    )
