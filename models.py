from app import db
from datetime import datetime

# Expense Category Models
class ExpenseCategory(db.Model):
    """General expense categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'

class AdvanceCategory(db.Model):
    """Advance salary categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AdvanceCategory {self.name}>'

class CreditCategory(db.Model):
    """Credit sales categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CreditCategory {self.name}>'

class CashbackCategory(db.Model):
    """Cashback categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CashbackCategory {self.name}>'

class ExpenseCategorySamer(db.Model):
    """Samer's specific expense categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ExpenseCategorySamer {self.name}>'

# Transaction Models
class ExpenseTransaction(db.Model):
    """Individual expense transactions"""
    id = db.Column(db.Integer, primary_key=True)
    daily_close_id = db.Column(db.Integer, db.ForeignKey('daily_close.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('ExpenseCategory', backref='transactions')

class AdvanceTransaction(db.Model):
    """Individual advance salary transactions"""
    id = db.Column(db.Integer, primary_key=True)
    daily_close_id = db.Column(db.Integer, db.ForeignKey('daily_close.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('advance_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('AdvanceCategory', backref='transactions')

class CreditTransaction(db.Model):
    """Individual credit sales transactions"""
    id = db.Column(db.Integer, primary_key=True)
    daily_close_id = db.Column(db.Integer, db.ForeignKey('daily_close.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('credit_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('CreditCategory', backref='transactions')

class CashbackTransaction(db.Model):
    """Individual cashback transactions"""
    id = db.Column(db.Integer, primary_key=True)
    daily_close_id = db.Column(db.Integer, db.ForeignKey('daily_close.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('cashback_category.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('CashbackCategory', backref='transactions')

class SamerExpenseTransaction(db.Model):
    """Samer's expense transactions"""
    id = db.Column(db.Integer, primary_key=True)
    daily_close_id = db.Column(db.Integer, db.ForeignKey('daily_close.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_category_samer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    category = db.relationship('ExpenseCategorySamer', backref='transactions')

class DailyClose(db.Model):
    """Model for storing daily close transactions"""
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Input fields
    main_reading = db.Column(db.Float, nullable=False, default=0.0)
    dr_smashed = db.Column(db.Float, nullable=False, default=0.0)
    ahmad_expenses = db.Column(db.Float, nullable=False, default=0.0)
    
    # Calculated fields
    adjusted_reading = db.Column(db.Float, nullable=False, default=0.0)
    five_percent = db.Column(db.Float, nullable=False, default=0.0)
    actual_cash = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relationship to transactions
    expense_transactions = db.relationship('ExpenseTransaction', backref='daily_close', cascade='all, delete-orphan')
    advance_transactions = db.relationship('AdvanceTransaction', backref='daily_close', cascade='all, delete-orphan')
    credit_transactions = db.relationship('CreditTransaction', backref='daily_close', cascade='all, delete-orphan')
    cashback_transactions = db.relationship('CashbackTransaction', backref='daily_close', cascade='all, delete-orphan')
    samer_expense_transactions = db.relationship('SamerExpenseTransaction', backref='daily_close', cascade='all, delete-orphan')
    
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