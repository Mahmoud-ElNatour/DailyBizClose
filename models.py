from app import db
from datetime import datetime

class DailyClose(db.Model):
    """Model for storing daily close transactions"""
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Input fields
    main_reading = db.Column(db.Float, nullable=False, default=0.0)
    dr_smashed = db.Column(db.Float, nullable=False, default=0.0)
    ahmad_expenses = db.Column(db.Float, nullable=False, default=0.0)
    daily_expenses = db.Column(db.Float, nullable=False, default=0.0)
    daily_advances = db.Column(db.Float, nullable=False, default=0.0)
    credit_sales = db.Column(db.Float, nullable=False, default=0.0)
    cashback = db.Column(db.Float, nullable=False, default=0.0)
    
    # Calculated fields
    adjusted_reading = db.Column(db.Float, nullable=False, default=0.0)
    five_percent = db.Column(db.Float, nullable=False, default=0.0)
    actual_cash = db.Column(db.Float, nullable=False, default=0.0)
    
    def __repr__(self):
        return f'<DailyClose {self.date_created.strftime("%Y-%m-%d")}>'

class User(db.Model):
    """Basic User model for future authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'