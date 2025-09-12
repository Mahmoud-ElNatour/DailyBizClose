from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Create a separate db instance for models
db = SQLAlchemy(model_class=Base)

class DailyClosing(db.Model):
    """Daily closing records with calculated totals"""
    __tablename__ = 'daily_closing'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_expenses = db.Column(db.Float, nullable=False, default=0.0)
    total_advance = db.Column(db.Float, nullable=False, default=0.0)
    total_credit = db.Column(db.Float, nullable=False, default=0.0)
    total_cashback = db.Column(db.Float, nullable=False, default=0.0)
    five_percent = db.Column(db.Float, nullable=False, default=0.0)
    total_cashout = db.Column(db.Float, nullable=False, default=0.0)
    actual_cash = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('Expenses', backref='daily_closing', cascade='all, delete-orphan')
    ahmad_mistrah_expenses = db.relationship('AhmadMistrahExpenses', backref='daily_closing', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DailyClosing {self.date.strftime("%Y-%m-%d")}>'

class Expenses(db.Model):
    """Individual expense records"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('receivers.id'), nullable=True)
    
    def __repr__(self):
        return f'<Expenses {self.amount} on {self.date.strftime("%Y-%m-%d")}>'

class AhmadMistrahExpenses(db.Model):
    """Ahmad Mistrah expenses records"""
    __tablename__ = 'ahmad_mistrah_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    
    def __repr__(self):
        return f'<AhmadMistrahExpenses {self.amount} on {self.date.strftime("%Y-%m-%d")}>'

class Receivers(db.Model):
    """Recipients of payments/expenses"""
    __tablename__ = 'receivers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('Expenses', backref='receiver')
    
    def __repr__(self):
        return f'<Receivers {self.name}>'

class Customers(db.Model):
    """Customer records with balances"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)
    phone_number = db.Column(db.String(20))
    
    def __repr__(self):
        return f'<Customers {self.username}>'

class Employees(db.Model):
    """Employee records with salary calculations"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))
    position = db.Column(db.String(50))
    year = db.Column(db.Integer, nullable=False, default=lambda: datetime.utcnow().year)
    month = db.Column(db.Integer, nullable=False, default=lambda: datetime.utcnow().month)
    base_salary = db.Column(db.Float, nullable=False, default=0.0)
    working_days = db.Column(db.Float, nullable=False, default=0.0)
    actual_working_days = db.Column(db.Float, nullable=False, default=0.0)
    deductions = db.Column(db.Float, nullable=False, default=0.0)
    advance = db.Column(db.Float, nullable=False, default=0.0)
    actual_salary = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    
    def calculate_salary(self):
        """Calculate actual salary and total based on working days"""
        if self.working_days > 0:
            daily_rate = self.base_salary / self.working_days
            self.actual_salary = daily_rate * self.actual_working_days - self.deductions-self.advance
            if self.actual_salary<0:
                self.total=0.0
            else:
                self.total=self.actual_salary
        else:
            self.actual_salary = 0.0
            self.total = 0.0
    
    def __repr__(self):
        return f'<Employees {self.name}>'

class User(db.Model, UserMixin):
    """Basic User model for future authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'