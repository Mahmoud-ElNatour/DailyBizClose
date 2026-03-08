from decimal import Decimal
from datetime import datetime, timezone
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
    main_reading = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    dr_smashed = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    adjusted_reading = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_expenses = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_advance = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_credit = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_cashback = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    five_percent = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_cashout = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total_deductions = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    actual_cash = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('Expenses', backref='daily_closing', cascade='all, delete-orphan')
    ahmad_mistrah_expenses = db.relationship('AhmadMistrahExpenses', backref='daily_closing', cascade='all, delete-orphan')
    samer_expenses = db.relationship('SamerExpenses', backref='daily_closing', cascade='all, delete-orphan')
    advances = db.relationship('Advances', backref='daily_closing', cascade='all, delete-orphan')
    credits = db.relationship('Credits', backref='daily_closing', cascade='all, delete-orphan')
    cashbacks = db.relationship('Cashbacks', backref='daily_closing', cascade='all, delete-orphan')
    deductions_rel = db.relationship('Deductions', backref='daily_closing', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DailyClosing {self.date.strftime("%Y-%m-%d")}>'

class Expenses(db.Model):
    """Individual expense records"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
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
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('ahmad_expense_receivers.id'), nullable=True)
    
    def __repr__(self):
        return f'<AhmadMistrahExpenses {self.amount} on {self.date.strftime("%Y-%m-%d")}>'

class AhmadExpenseReceivers(db.Model):
    """Recipients of Ahmad's expenses"""
    __tablename__ = 'ahmad_expense_receivers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('AhmadMistrahExpenses', backref='receiver')
    
    def __repr__(self):
        return f'<AhmadExpenseReceivers {self.name}>'

class SamerExpenses(db.Model):
    """Samer expenses records"""
    __tablename__ = 'samer_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('samer_expense_receivers.id'), nullable=True)
    
    def __repr__(self):
        return f'<SamerExpenses {self.amount} on {self.date.strftime("%Y-%m-%d")}>'

class SamerExpenseReceivers(db.Model):
    """Recipients of Samer's expenses"""
    __tablename__ = 'samer_expense_receivers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('SamerExpenses', backref='receiver')
    
    def __repr__(self):
        return f'<SamerExpenseReceivers {self.name}>'

class Receivers(db.Model):
    """Recipients of payments/expenses"""
    __tablename__ = 'receivers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    
    # Relationships
    expenses = db.relationship('Expenses', backref='receiver')
    
    def __repr__(self):
        return f'<Receivers {self.name}>'

class Customers(db.Model):
    """Customer records with balances"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    phone_number = db.Column(db.String(20))
    
    # Relationships
    credits_rel = db.relationship('Credits', backref='customer')
    cashbacks_rel = db.relationship('Cashbacks', backref='customer')
    
    def __repr__(self):
        return f'<Customers {self.username}>'

class Employees(db.Model):
    """Employee records with basic info"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))
    position = db.Column(db.String(50))
    base_salary = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    monthly_records = db.relationship('EmployeeWorking', backref='employee', cascade='all, delete-orphan')
    advances_rel = db.relationship('Advances', backref='employee')
    deductions_list = db.relationship('Deductions', backref='employee')
    
    def __repr__(self):
        return f'<Employees {self.name}>'

class EmployeeWorking(db.Model):
    """Monthly employee records for salary calculations"""
    __tablename__ = 'employee_working'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')
    working_days = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    actual_working_days = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    deductions_total = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    advance_total = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    actual_salary = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    total = db.Column(db.Numeric(12, 2), nullable=False, default=0.0)
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    is_working = db.Column(db.Boolean, default=True)
    note = db.Column(db.String(500))
    
    def calculate_salary(self):
        """Calculate actual salary and total based on working days and status"""
        if not self.is_working:
            self.actual_salary = 0.0
            self.total = 0.0
            return

        try:
            working_days = float(self.working_days)
            # Use base_salary from the parent employee
            base_salary = float(self.employee.base_salary)
            actual_working_days = float(self.actual_working_days)
            deductions = float(self.deductions_total)
            advance = float(self.advance_total)
        except (TypeError, ValueError, AttributeError):
            self.actual_salary = 0.0
            self.total = 0.0
            return

        if working_days > 0:
            daily_rate = base_salary / working_days
            self.actual_salary = daily_rate * actual_working_days - deductions - advance
        else:
            self.actual_salary = -deductions - advance

        if self.actual_salary < 0:
            self.total = 0.0
        else:
            self.total = self.actual_salary
    
    def __repr__(self):
        return f'<EmployeeWorking ID:{self.id} Emp:{self.employee_id} {self.year}-{self.month}>'

class Advances(db.Model):
    """Employee salary advances from daily close"""
    __tablename__ = 'advances'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)

class Credits(db.Model):
    """Customer credit sales from daily close"""
    __tablename__ = 'credits'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)

class Cashbacks(db.Model):
    """Customer cashbacks from daily close"""
    __tablename__ = 'cashbacks'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)

class Deductions(db.Model):
    """Employee salary deductions from daily close"""
    __tablename__ = 'deductions_records'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(500))
    daily_closing_id = db.Column(db.Integer, db.ForeignKey('daily_closing.id'), nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)

class User(db.Model, UserMixin):
    """Basic User model for future authentication"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<User {self.username}>'

class Logs(db.Model):
    """Audit logs for system activities"""
    __tablename__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    level = db.Column(db.String(20), nullable=False, index=True) # SUCCESS, INFO, WARNING, ERROR
    request_id = db.Column(db.String(100), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(100), index=True)
    ip_address = db.Column(db.String(45))
    method = db.Column(db.String(10))
    path = db.Column(db.String(255))
    action = db.Column(db.String(100), index=True)
    status_code = db.Column(db.Integer, index=True)
    message = db.Column(db.String(500))
    details_json = db.Column(db.Text) # JSON string
    duration_ms = db.Column(db.Integer)
    
    def __repr__(self):
        return f'<Logs {self.id} - {self.action} - {self.level}>'

class SiteSettings(db.Model):
    """Dynamic settings for the public landing page"""
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True) # Null represents a truly missing value
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    updated_by = db.relationship('User', backref='settings_updates')

    def __repr__(self):
        return f'<SiteSettings {self.key}>'

class SiteGalleryImages(db.Model):
    """Images displayed on the public landing page gallery"""
    __tablename__ = 'site_gallery_images'
    
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.Text, nullable=False) # Will store the relative static path or full URL
    alt_text = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<SiteGalleryImages {self.id} Active:{self.is_active}>'

class MenuCategory(db.Model):
    """Categories for the public menu"""
    __tablename__ = 'menu_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    items = db.relationship('MenuItem', backref='category', cascade='all, delete-orphan', lazy=True)
    
    def __repr__(self):
        return f'<MenuCategory {self.name}>'

class MenuItem(db.Model):
    """Items within menu categories"""
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    image_url = db.Column(db.Text, nullable=True)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<MenuItem {self.name} (${self.price})>'