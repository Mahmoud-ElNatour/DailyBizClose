from app import app
from models import db
# Import all your models here so SQLAlchemy knows about them
import models

with app.app_context():
    # db.create_all() safely creates tables that don't exist yet
    # It will NOT overwrite or drop existing tables or their data.
    db.create_all()
    print("Database tables created successfully (existing tables and data were left untouched).")
