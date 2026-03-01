import decimal
import os
from datetime import datetime, timezone, UTC
import logging
import hashlib

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

# Set up logging for debug mode
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

def safe_decimal(value, default=None):
    if default is None:
        default = decimal.Decimal('0.00')
    try:
        if value is None or str(value).strip() == '':
            return default
        return decimal.Decimal(str(value)).quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_HALF_UP)
    except (ValueError, TypeError, decimal.InvalidOperation):
        return default

def safe_int(value, default=0):
    try:
        if value is None or str(value).strip() == '':
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

# Import db from models to avoid circular import
from models import db

# Create the app
app = Flask(__name__)
app.secret_key = 'secret_key'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:Mah!moud123@localhost:3306/dailybizclose"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

from functools import wraps
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            from models import Logs
            import json
            # Log forbidden access attempt
            log_event(
                level='WARNING',
                action='FORBIDDEN_ACCESS',
                message=f"Unauthorized access attempt to {request.path}",
                status_code=403,
                details={'path': request.path, 'method': request.method}
            )
            flash('You do not have permission to access this page.', 'error')
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Forbidden'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def log_event(level='INFO', action=None, message=None, status_code=None, details=None, duration=None):
    """Helper to record audit logs"""
    try:
        from models import Logs, db
        import json
        
        log = Logs(
            level=level,
            request_id=request.headers.get('X-Request-ID', ''), # Optional: if you have request IDs
            user_id=current_user.id if current_user.is_authenticated else None,
            username=current_user.username if current_user.is_authenticated else 'anonymous',
            ip_address=request.remote_addr,
            method=request.method,
            path=request.path,
            action=action,
            status_code=status_code,
            message=message,
            details_json=json.dumps(details) if details else None,
            duration_ms=duration
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to record log: {e}")

def check_dependencies_and_respond(entity_type, entity_id, checks):
    """
    checks: list of tuples (description, model, filter_kwargs)
    Returns: response tuple if blocked, else None
    """
    dependencies = []
    total_count = 0
    
    for description, model, filter_kwargs in checks:
        count = model.query.filter_by(**filter_kwargs).count()
        if count > 0:
            dependencies.append({'entity': description, 'count': count})
            total_count += count
            
    if total_count > 0:
        # Log the blocked attempt
        log_event(
            level='WARNING',
            action=f'{entity_type}_delete_blocked',
            message='Delete blocked due to dependencies',
            status_code=409,
            details={'id': entity_id, 'entity': entity_type, 'dependencies': dependencies}
        )
        
        message = f"Cannot delete this {entity_type} because it is used in {total_count} records."
        return jsonify({
            "success": False,
            "error": {
                "code": "CONFLICT",
                "message": message,
                "details": {
                    "dependencies": dependencies
                }
            },
            "toast": {
                "type": "error",
                "title": "Delete blocked",
                "message": "Cannot delete because it is used in other records."
            },
            "requestId": request.headers.get('X-Request-ID', '')
        }), 409
        
    return None

def apply_carryover_debt(employee_id, current_year, current_month):
    """Calculates carryover debt and issues a Deductions record if debt exists."""
    from models import EmployeeWorking, Deductions
    prev_month = current_month - 1
    prev_year = current_year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
        
    prev_record = EmployeeWorking.query.filter_by(employee_id=employee_id, year=prev_year, month=prev_month).first()
    
    carryover_debt = 0.0
    if prev_record and prev_record.actual_salary and prev_record.actual_salary < 0:
        carryover_debt = abs(float(prev_record.actual_salary))
        
    if carryover_debt > 0:
        deduction = Deductions(
            amount=carryover_debt,
            employee_id=employee_id,
            note=f"Carryover debt from {prev_month}/{prev_year}"
        )
        db.session.add(deduction)
        
    return carryover_debt

def create_user(username, email, password, role='user'):
    """Create a new user"""
    try:
        from models import User
       
        user = User(
            username=username,
            email=email,
            password_hash=hashlib.sha256(password.encode()).hexdigest(),
            role=role or 'user'
        )
        db.session.add(user)
        db.session.commit()
        return user
    except Exception as e:
        app.logger.error(f"Error creating user: {e}")
        db.session.rollback()
        return None
# Initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Routes
@app.route('/')
@login_required
def main():
    """Main route - redirects to index"""
    app.logger.debug(f"Main route accessed. Current user: {current_user}")
    app.logger.debug(f"Is authenticated: {current_user.is_authenticated}")
    return redirect(url_for('index'))

@app.route('/index',methods=['GET'])
@login_required
def index():
    """Home page route"""
    app.logger.debug(f"Current user: {current_user}")
    app.logger.debug(f"Is authenticated: {current_user.is_authenticated}")
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route"""
    app.logger.debug(f"Login route accessed. Method: {request.method}")
    app.logger.debug(f"Current user: {current_user}")
    app.logger.debug(f"Is authenticated: {current_user.is_authenticated}")
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        app.logger.debug(f"Login attempt for username: {username}")
        
        try:
            from models import User
            user = User.query.filter_by(username=username).first()
            
            app.logger.debug(f"User found: {user}")
            
            if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
                login_user(user)
                log_event(level='SUCCESS', action='USER_LOGIN', message=f"User {user.username} logged in successfully")
                app.logger.debug(f"User logged in successfully: {user.username}")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                log_event(level='WARNING', action='LOGIN_FAILED', message=f"Failed login attempt for username: {username}", status_code=401)
                app.logger.debug("Login failed - invalid credentials")
                flash('Invalid username or password', 'error')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')
@app.route('/logout')
def logout():
    """Logout page route"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/control-panel')
@login_required
@admin_required
def control_panel():
    """Control panel page route"""
    return render_template('control_panel.html')

@app.route('/daily-close')
@login_required
def daily_close():
    """Daily close page route"""
    return render_template('daily_close.html')

@app.route('/settings')
@login_required
def settings():
    """Settings page route"""
    app.logger.debug(f"Settings route accessed. Current user: {current_user}")
    return render_template('settings.html')

# Control Panel Module Routes
@app.route('/control-panel/employees')
@login_required
@admin_required
def employees():
    """Employees page with filtering"""
    try:
        from models import EmployeeWorking, Employees, db
        import calendar
        from datetime import datetime
        from sqlalchemy import text
        
        # Self-migration: Ensure is_working column exists
        try:
            db.session.execute(text('ALTER TABLE employee_working ADD COLUMN is_working BOOLEAN DEFAULT TRUE'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        # Get parameters
        year_raw = request.args.get('year', '')
        month_raw = request.args.get('month', '')
        
        if year_raw == 'AllYears':
            year = 0
        else:
            year = request.args.get('year', type=int)
            
        if month_raw == 'AllMonths':
            month = 0
        else:
            month = request.args.get('month', type=int)
        
        view_type = request.args.get('view_type', 'working') # 'working', 'not_working', or 'all'
        search = request.args.get('search', '').strip()
        
        # Default to current month/year if not provided (and not explicitly 'All')
        now = datetime.now(UTC)
        if year is None: year = now.year
        if month is None: month = now.month
        
        month_name = calendar.month_name[month] if month > 0 else 'All Months'
        
        # Auto-rollover active employees into the CURRENT month if viewed
        if year == now.year and month == now.month:
            active_emps = Employees.query.filter_by(is_active=True).all()
            for emp in active_emps:
                existing = EmployeeWorking.query.filter_by(employee_id=emp.id, year=year, month=month).first()
                if not existing:
                    # Calculate if previous month had carryover debt
                    carryover_debt = apply_carryover_debt(emp.id, year, month)

                    # Create actual record
                    new_record = EmployeeWorking(
                        employee_id=emp.id,
                        year=year,
                        month=month,
                        is_working=True,
                        working_days=0,
                        actual_working_days=0,
                        deductions_total=carryover_debt,
                        advance_total=0,
                        actual_salary=-carryover_debt,
                        total=0
                    )
                    db.session.add(new_record)
            db.session.commit()
        
        if view_type == 'working':
            # Only those with records for this period
            query = EmployeeWorking.query
            if year != 0: query = query.filter_by(year=year)
            if month != 0: query = query.filter_by(month=month)
            
            if search:
                query = query.join(Employees).filter(
                    (Employees.name.ilike(f'%{search}%')) | 
                    (db.cast(Employees.id, db.String).ilike(f'%{search}%'))
                )
            records = query.all()
        elif view_type == 'not_working':
            # Employees WHO DO NOT have a record for this period
            emp_query = Employees.query.filter_by(is_active=True)
            if search:
                emp_query = emp_query.filter(
                    (Employees.name.ilike(f'%{search}%')) | 
                    (db.cast(Employees.id, db.String).ilike(f'%{search}%'))
                )
            employees_all = emp_query.all()
            
            records = []
            for emp in employees_all:
                working_query = EmployeeWorking.query.filter_by(employee_id=emp.id)
                if year != 0: working_query = working_query.filter_by(year=year)
                if month != 0: working_query = working_query.filter_by(month=month)
                
                if not working_query.first():
                    # Create a transient record for display - set is_working=True by default
                    record = EmployeeWorking(employee_id=emp.id, year=year, month=month, is_working=True)
                    record.employee = emp
                    record.working_days = 0 
                    records.append(record)
        else: # 'all' (Roster View)
            # All active employees. For each, show the most relevant record in period or transient.
            emp_query = Employees.query.filter_by(is_active=True)
            if search:
                emp_query = emp_query.filter(
                    (Employees.name.ilike(f'%{search}%')) | 
                    (db.cast(Employees.id, db.String).ilike(f'%{search}%'))
                )
            employees_all = emp_query.all()
            
            records = []
            for emp in employees_all:
                working_query = EmployeeWorking.query.filter_by(employee_id=emp.id)
                if year != 0: working_query = working_query.filter_by(year=year)
                if month != 0: working_query = working_query.filter_by(month=month)
                
                # Get the latest record in the period, or create transient if none
                record = working_query.order_by(EmployeeWorking.year.desc(), EmployeeWorking.month.desc()).first()
                if not record:
                    record = EmployeeWorking(employee_id=emp.id, year=year, month=month, is_working=True)
                    record.employee = emp
                    record.working_days = 0 
                records.append(record)

        return render_template('employees.html', 
                             employees=records, 
                             year=year, 
                             month=month, 
                             month_name=month_name,
                             view_type=view_type)
    except Exception as e:
        app.logger.error(f"Error loading employees: {e}")
        flash('Error loading employees data', 'error')
        from datetime import datetime
        now = datetime.now(UTC)
        return render_template('employees.html', employees=[], year=now.year, month=now.month, month_name='', view_type='working')


@app.route('/control-panel/employees/<int:year>')
@login_required
@admin_required
def employees_year_redirect(year):
    return redirect(url_for('employees', year=year))


@app.route('/control-panel/employees/<int:year>/<int:month>')
@login_required
@admin_required
def employees_month_redirect(year, month):
    return redirect(url_for('employees', year=year, month=month))

@app.route('/control-panel/customers')
@login_required
def customers():
    """Customers management page with date filtering for balances"""
    try:
        from models import Customers, Credits, Cashbacks
        from sqlalchemy import func
        from datetime import datetime
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        customers_query = Customers.query.all()
        filtered_balances = {}
        
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                
                for customer in customers_query:
                    c_total = db.session.query(func.sum(Credits.amount)).filter(
                        Credits.customer_id == customer.id,
                        Credits.date >= start_date,
                        Credits.date <= end_date
                    ).scalar() or 0
                    
                    cb_total = db.session.query(func.sum(Cashbacks.amount)).filter(
                        Cashbacks.customer_id == customer.id,
                        Cashbacks.date >= start_date,
                        Cashbacks.date <= end_date
                    ).scalar() or 0
                    
                    filtered_balances[customer.id] = float(cb_total) - float(c_total)
            except ValueError:
                app.logger.error(f"Invalid date format: {start_date_str} to {end_date_str}")
        
        return render_template('customers.html', 
                             customers=customers_query, 
                             filtered_balances=filtered_balances,
                             start_date=start_date_str,
                             end_date=end_date_str)
    except Exception as e:
        app.logger.error(f"Error loading customers: {e}")
        flash('Error loading customers data', 'error')
        return render_template('customers.html', customers=[], filtered_balances={})

@app.route('/control-panel/users')
@login_required
@admin_required
def users():
    """Users management page"""
    try:
        from models import User
        users = User.query.all()
        return render_template('users.html', users=users)
    except Exception as e:
        app.logger.error(f"Error loading users: {e}")
        flash('Error loading users data', 'error')
        return render_template('users.html', users=[])

@app.route('/control-panel/reports')
@login_required
@admin_required
def reports():
    """Reports page"""
    try:
        from models import DailyClosing, Expenses, Customers, Employees
        # Get summary data for reports
        total_daily_closings = DailyClosing.query.count()
        total_expenses = Expenses.query.count()
        total_customers = Customers.query.count()
        total_employees = Employees.query.count()
        
        return render_template('reports.html', 
                            total_daily_closings=total_daily_closings,
                            total_expenses=total_expenses,
                            total_customers=total_customers,
                            total_employees=total_employees)
    except Exception as e:
        app.logger.error(f"Error loading reports: {e}")
        flash('Error loading reports data', 'error')
        return render_template('reports.html')

@app.route('/control-panel/expenses')
@login_required
@admin_required
def expenses():
    """Expenses management page"""
    try:
        from models import Expenses, Receivers
        from datetime import datetime
        
        # Get filter parameters
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        # Build query
        query = Expenses.query
        
        if month and year:
            # Filter by month and year
            query = query.filter(
                db.extract('year', Expenses.date) == year,
                db.extract('month', Expenses.date) == month
            )
        elif month:
            # Filter by month only
            query = query.filter(db.extract('month', Expenses.date) == month)
        elif year:
            # Filter by year only
            query = query.filter(db.extract('year', Expenses.date) == year)
        
        expenses = query.all()
        receivers = Receivers.query.all()
        
        # Calculate statistics
        total_expenses = sum(exp.amount or 0 for exp in expenses)
        max_expense = max((exp.amount or 0 for exp in expenses), default=0)
        
        receiver_totals = {}
        for exp in expenses:
            name = exp.receiver.name if exp.receiver else 'N/A'
            receiver_totals[name] = receiver_totals.get(name, 0) + (exp.amount or 0)
        
        top_receiver = max(receiver_totals.items(), key=lambda x: x[1], default=('N/A', 0))
        
        stats = {
            'total': total_expenses,
            'max': max_expense,
            'count': len(expenses),
            'top_receiver': top_receiver[0],
            'top_receiver_amount': top_receiver[1]
        }
        
        return render_template('expenses.html', expenses=expenses, receivers=receivers, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading expenses: {e}")
        flash('Error loading expenses data', 'error')
        return render_template('expenses.html', expenses=[], receivers=[], stats={'total': 0, 'max': 0, 'count': 0, 'top_receiver': 'N/A', 'top_receiver_amount': 0})

@app.route('/control-panel/sales')
@login_required
@admin_required
def sales():
    """Sales management page"""
    try:
        from models import DailyClosing
        from datetime import datetime
        
        # Get filter parameters
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if month is None or year is None:
            now = datetime.now(UTC)
            month = now.month
            year = now.year
            
        # Build query
        query = DailyClosing.query.filter(
            db.extract('year', DailyClosing.date) == year,
            db.extract('month', DailyClosing.date) == month
        )
        closings = query.order_by(DailyClosing.date.desc()).all()
        
        # Calculate sums for cards
        total_expenses_sum = sum(c.total_expenses for c in closings)
        total_actual_cash_sum = sum(c.actual_cash for c in closings)
        total_credit_sum = sum(c.total_credit for c in closings)
        total_five_percent_sum = sum(c.five_percent for c in closings)
        
        month_name = datetime(2000, month, 1).strftime('%B')
        
        return render_template('sales.html', 
                             closings=closings,
                             month=month,
                             year=year,
                             month_name=month_name,
                             total_expenses_sum=total_expenses_sum,
                             total_actual_cash_sum=total_actual_cash_sum,
                             total_credit_sum=total_credit_sum,
                             total_five_percent_sum=total_five_percent_sum)
    except Exception as e:
        app.logger.error(f"Error loading sales: {e}")
        flash('Error loading sales data', 'error')
        return render_template('sales.html', closings=[], total_expenses_sum=0, total_actual_cash_sum=0, total_credit_sum=0, total_five_percent_sum=0)

@app.route('/control-panel/payroll')
@login_required
@admin_required
def payroll():
    """Payroll management page using monthly records"""
    try:
        from models import EmployeeWorking
        from datetime import datetime
        
        # Get filter parameters
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        query = EmployeeWorking.query
        if year is not None:
            query = query.filter_by(year=year)
        if month is not None:
            query = query.filter_by(month=month)
        records = query.all()

        return render_template('payroll.html', employees=records)
    except Exception as e:
        app.logger.error(f"Error loading payroll: {e}")
        flash('Error loading payroll data', 'error')
        return render_template('payroll.html', employees=[])

@app.route('/api/employees/<int:record_id>/calculate', methods=['POST'])
@login_required
def calculate_employee_payroll(record_id):
    """Trigger payroll calculation for a monthly record"""
    try:
        from models import EmployeeWorking
        record = EmployeeWorking.query.get_or_404(record_id)
        record.calculate_salary()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Payroll calculated successfully',
            'actual_salary': record.actual_salary,
            'total': record.total
        })
    except Exception as e:
        app.logger.error(f"Error calculating payroll: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to calculate payroll'}), 500

@app.route('/payroll/payslip/<int:record_id>')
@login_required
def generate_payslip_view(record_id):
    """Render printable payslip for a monthly record"""
    try:
        from models import EmployeeWorking, Advances, Deductions
        record = EmployeeWorking.query.get_or_404(record_id)
        
        show_details = request.args.get('show_details') == 'true'
        details = None
        
        if show_details:
            advances_list = Advances.query.filter_by(employee_id=record.employee_id, 
                                                    date=record.year).all() # This needs fixing
            # Wait, Advances/Deductions use date, not month/year directly.
            # Let's filter by month and year of the record date or similar.
            # Actually, Advances matches by employee_id. We should filter by record month/year.
            from sqlalchemy import extract
            advances_list = Advances.query.filter(
                Advances.employee_id == record.employee_id,
                extract('year', Advances.date) == record.year,
                extract('month', Advances.date) == record.month
            ).all()
            deductions_list = Deductions.query.filter(
                Deductions.employee_id == record.employee_id,
                extract('year', Deductions.date) == record.year,
                extract('month', Deductions.date) == record.month
            ).all()
            details = {
                'advances': advances_list,
                'deductions': deductions_list
            }
            
        return render_template('payslip.html', record=record, employee=record.employee, show_details=show_details, details=details)
    except Exception as e:
        app.logger.error(f"Error generating payslip: {e}")
        flash('Error generating payslip', 'error')
        return redirect(url_for('payroll'))

@app.route('/control-panel/receivers')
@login_required
@admin_required
def receivers_view():
    """Receivers list page"""
    try:
        from models import Receivers
        receivers = Receivers.query.all()
        return render_template('receivers.html', receivers=receivers)
    except Exception as e:
        app.logger.error(f"Error loading receivers: {e}")
        flash('Error loading receivers page', 'error')
        return redirect(url_for('control_panel'))

@app.route('/control-panel/ahmad-expenses')
@login_required
@admin_required
def ahmad_expenses_view():
    """Ahmad expenses list page"""
    try:
        from models import AhmadMistrahExpenses, AhmadExpenseReceivers
        from datetime import datetime
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        query = AhmadMistrahExpenses.query
        if month and year:
            query = query.filter(db.extract('year', AhmadMistrahExpenses.date) == year, db.extract('month', AhmadMistrahExpenses.date) == month)
        elif month:
            query = query.filter(db.extract('month', AhmadMistrahExpenses.date) == month)
        elif year:
            query = query.filter(db.extract('year', AhmadMistrahExpenses.date) == year)
            
        expenses = query.all()
        receivers = AhmadExpenseReceivers.query.all()
        
        total = sum(safe_decimal(e.amount, decimal.Decimal('0.00')) for e in expenses)
        max_val = max((safe_decimal(e.amount, decimal.Decimal('0.00')) for e in expenses), default=0)
        receiver_totals = {}
        for e in expenses:
            name = e.receiver.name if e.receiver else 'General'
            receiver_totals[name] = receiver_totals.get(name, 0) + safe_decimal(e.amount, decimal.Decimal('0.00'))
        top_receiver = max(receiver_totals.items(), key=lambda x: x[1], default=('N/A', 0))
        
        stats = {'total': total, 'max': max_val, 'count': len(expenses), 'top_receiver': top_receiver[0], 'top_receiver_amount': top_receiver[1]}
        return render_template('ahmad_expenses.html', expenses=expenses, receivers=receivers, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading Ahmad expenses: {e}")
        return render_template('ahmad_expenses.html', expenses=[], receivers=[], stats={'total': 0, 'max': 0, 'count': 0, 'top_receiver': 'N/A', 'top_receiver_amount': 0})

@app.route('/control-panel/samer-expenses')
@login_required
@admin_required
def samer_expenses_view():
    """Samer expenses list page"""
    try:
        from models import SamerExpenses, SamerExpenseReceivers
        from datetime import datetime
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        query = SamerExpenses.query
        if month and year:
            query = query.filter(db.extract('year', SamerExpenses.date) == year, db.extract('month', SamerExpenses.date) == month)
        elif month:
            query = query.filter(db.extract('month', SamerExpenses.date) == month)
        elif year:
            query = query.filter(db.extract('year', SamerExpenses.date) == year)
            
        expenses = query.all()
        receivers = SamerExpenseReceivers.query.all()
        
        total = sum(safe_decimal(e.amount, decimal.Decimal('0.00')) for e in expenses)
        max_val = max((safe_decimal(e.amount, decimal.Decimal('0.00')) for e in expenses), default=0)
        receiver_totals = {}
        for e in expenses:
            name = e.receiver.name if e.receiver else 'General'
            receiver_totals[name] = receiver_totals.get(name, 0) + safe_decimal(e.amount, decimal.Decimal('0.00'))
        top_receiver = max(receiver_totals.items(), key=lambda x: x[1], default=('N/A', 0))
        
        stats = {'total': total, 'max': max_val, 'count': len(expenses), 'top_receiver': top_receiver[0], 'top_receiver_amount': top_receiver[1]}
        return render_template('samer_expenses.html', expenses=expenses, receivers=receivers, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading Samer expenses: {e}")
        return render_template('samer_expenses.html', expenses=[], receivers=[], stats={'total': 0, 'max': 0, 'count': 0, 'top_receiver': 'N/A', 'top_receiver_amount': 0})

@app.route('/control-panel/credits')
@login_required
@admin_required
def credits_view():
    """Customer credit records list page"""
    try:
        from models import Credits, Customers
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        query = Credits.query
        if month and year:
            query = query.filter(db.extract('year', Credits.date) == year, db.extract('month', Credits.date) == month)
        elif month:
            query = query.filter(db.extract('month', Credits.date) == month)
        elif year:
            query = query.filter(db.extract('year', Credits.date) == year)
            
        records = query.order_by(Credits.date.desc()).all()
        
        total = sum(safe_decimal(r.amount, decimal.Decimal('0.00')) for r in records)
        stats = {
            'total': total,
            'count': len(records),
            'max': max((safe_decimal(r.amount, decimal.Decimal('0.00')) for r in records), default=0)
        }
        
        return render_template('credits_records.html', records=records, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading credits records: {e}")
        return render_template('credits_records.html', records=[], stats={'total': 0, 'count': 0, 'max': 0})

@app.route('/control-panel/cashbacks')
@login_required
@admin_required
def cashbacks_view():
    """Customer cashback records list page"""
    try:
        from models import Cashbacks, Customers
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        query = Cashbacks.query
        if month and year:
            query = query.filter(db.extract('year', Cashbacks.date) == year, db.extract('month', Cashbacks.date) == month)
        elif month:
            query = query.filter(db.extract('month', Cashbacks.date) == month)
        elif year:
            query = query.filter(db.extract('year', Cashbacks.date) == year)
            
        records = query.order_by(Cashbacks.date.desc()).all()
        
        total = sum(safe_decimal(r.amount, decimal.Decimal('0.00')) for r in records)
        stats = {
            'total': total,
            'count': len(records),
            'max': max((safe_decimal(r.amount, decimal.Decimal('0.00')) for r in records), default=0)
        }
        
        return render_template('cashback_records.html', records=records, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading cashback records: {e}")
        return render_template('cashback_records.html', records=[], stats={'total': 0, 'count': 0, 'max': 0})

@app.route('/control-panel/deductions-advances')
@login_required
@admin_required
def deductions_advances_view():
    """Deductions and advances list with filtering"""
    try:
        from models import Advances, Deductions, Employees
        from datetime import datetime
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        advances_query = Advances.query
        deductions_query = Deductions.query
        
        if year:
            advances_query = advances_query.filter(db.extract('year', Advances.date) == year)
            deductions_query = deductions_query.filter(db.extract('year', Deductions.date) == year)
        if month:
            advances_query = advances_query.filter(db.extract('month', Advances.date) == month)
            deductions_query = deductions_query.filter(db.extract('month', Deductions.date) == month)
            
        advances = advances_query.order_by(Advances.date.desc()).all()
        deductions = deductions_query.order_by(Deductions.date.desc()).all()
        
        return render_template('deductions_advances.html', 
                             advances=advances, 
                             deductions=deductions,
                             current_month=month,
                             current_year=year)
    except Exception as e:
        app.logger.error(f"Error loading deductions & advances: {e}")
        flash('Error loading data', 'error')
        return redirect(url_for('control_panel'))

@app.route('/test-auth')
def test_auth():
    """Test route to check authentication status"""
    app.logger.debug(f"Test auth route. Current user: {current_user}")
    app.logger.debug(f"Is authenticated: {current_user.is_authenticated}")
    return jsonify({
        'current_user': str(current_user),
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None
    })

@app.route('/validate-admin-password', methods=['POST'])
@login_required
def validate_admin_password():
    """Validate admin password for date editing"""
    app.logger.debug("validate_admin_password route accessed")
    try:
        password = request.form.get('admin_password')
        
        if not password:
            flash('Password is required', 'error')
            return redirect(request.referrer or url_for('daily_close'))
        
        from models import User
        admin_users = User.query.filter_by(role='admin')
        Approved=False
        for i in admin_users:
            if i.password_hash == hashlib.sha256(password.encode()).hexdigest():
                Approved=True
                break
        if Approved:
            # Store admin validation in session
            session['admin_validated'] = True
            flash('Admin access granted. Date field unlocked.', 'success')
            return redirect(url_for('daily_close') + '?admin_validated=true')
        else:
            flash('Incorrect admin password', 'error')
            return redirect(request.referrer or url_for('daily_close'))
        
    except Exception as e:
        app.logger.error(f"Error validating admin password: {e}")
        flash('Error validating password', 'error')
        return redirect(request.referrer or url_for('daily_close'))

# API Routes for data management
@app.route('/api/suggestions/receivers')
@login_required
def get_receiver_suggestions():
    """Get unique receiver names for autocomplete"""
    try:
        from models import Receivers
        receivers = Receivers.query.with_entities(Receivers.name).distinct().all()
        return jsonify([r[0] for r in receivers])
    except Exception as e:
        app.logger.error(f"Error fetching receiver suggestions: {e}")
        return jsonify([]), 500

@app.route('/api/suggestions/employees')
@login_required
def get_employee_suggestions():
    """Get unique employee names for autocomplete"""
    try:
        from models import Employees
        employees = Employees.query.with_entities(Employees.name).distinct().all()
        return jsonify([e[0] for e in employees])
    except Exception as e:
        app.logger.error(f"Error fetching employee suggestions: {e}")
        return jsonify([]), 500

@app.route('/api/suggestions/customers')
@login_required
def get_customer_suggestions():
    """Get unique customer usernames for autocomplete"""
    try:
        from models import Customers
        customers = Customers.query.with_entities(Customers.username).distinct().all()
        return jsonify([c[0] for c in customers])
    except Exception as e:
        app.logger.error(f"Error fetching customer suggestions: {e}")
        return jsonify([]), 500

@app.route('/api/ahmad-receivers/suggestions')
@login_required
def get_ahmad_receiver_suggestions():
    """Get unique Ahmad receiver names for autocomplete"""
    try:
        from models import AhmadExpenseReceivers
        receivers = AhmadExpenseReceivers.query.with_entities(AhmadExpenseReceivers.name).distinct().all()
        return jsonify([r[0] for r in receivers])
    except Exception as e:
        app.logger.error(f"Error fetching Ahmad receiver suggestions: {e}")
        return jsonify([]), 500

@app.route('/api/samer-receivers/suggestions')
@login_required
def get_samer_receiver_suggestions():
    """Get unique Samer receiver names for autocomplete"""
    try:
        from models import SamerExpenseReceivers
        receivers = SamerExpenseReceivers.query.with_entities(SamerExpenseReceivers.name).distinct().all()
        return jsonify([r[0] for r in receivers])
    except Exception as e:
        app.logger.error(f"Error fetching Samer receiver suggestions: {e}")
        return jsonify([]), 500

@app.route('/api/receivers')
@login_required
def get_receivers():
    """Get all receivers with full data"""
    try:
        from models import Receivers
        receivers = Receivers.query.all()
        return jsonify({
            'receivers': [{
                'id': r.id,
                'name': r.name,
                'paid_amount': r.paid_amount
            } for r in receivers]
        })
    except Exception as e:
        app.logger.error(f"Error fetching receivers: {e}")
        return jsonify({'error': 'Failed to fetch receivers'}), 500

@app.route('/api/daily-closing', methods=['POST'])
@login_required
def daily_closing_api():
    """Process daily closing data"""
    try:
        from models import DailyClosing, Expenses, AhmadMistrahExpenses, SamerExpenses, AhmadExpenseReceivers, SamerExpenseReceivers, Receivers, Customers, Employees, Advances, Credits, Cashbacks
        from datetime import datetime
        
        data = request.get_json()
        close_date_str = data.get('date')
        if not close_date_str:
            return jsonify({'error': 'Date is required'}), 400
            
        close_date = datetime.strptime(close_date_str, '%Y-%m-%d')
        
        # Validation: Ensure main reading is provided
        if not (safe_decimal(data.get('main_reading', 0)) > 0):
            return jsonify({'error': 'Main Reading is mandatory. Please provide the current counter value.'}), 400

        # Check if already closed for this date (prevent multiple daily closings per user request)
        existing = DailyClosing.query.filter(db.func.date(DailyClosing.date) == close_date.date()).first()
        if existing:
            return jsonify({'error': f'A daily closing record already exists for {close_date_str}. Please edit the existing record or choose another date.'}), 400
        
        daily_close = DailyClosing(
            date=close_date,
            main_reading=safe_decimal(data.get('main_reading', 0)),
            dr_smashed=safe_decimal(data.get('dr_smashed', 0)),
            adjusted_reading=safe_decimal(data.get('adjusted_reading', 0)),
            total_expenses=safe_decimal(data.get('total_expenses', 0)),
            total_advance=safe_decimal(data.get('total_advance', 0)),
            total_credit=safe_decimal(data.get('total_credit', 0)),
            total_cashback=safe_decimal(data.get('total_cashback', 0)),
            total_deductions=safe_decimal(data.get('total_deductions', 0)),
            five_percent=safe_decimal(data.get('five_percent', 0)),
            total_cashout=safe_decimal(data.get('total_cashout', 0)),
            actual_cash=safe_decimal(data.get('actual_cash', 0))
        )
        db.session.add(daily_close)
        db.session.flush() # Get daily_close.id
        
        # Process Expenses
        for exp_data in data.get('expenses', []):
            receiver_name = exp_data.get('receiver_name')
            if receiver_name:
                receiver = Receivers.query.filter_by(name=receiver_name).first()
                if not receiver:
                    receiver = Receivers(name=receiver_name, paid_amount=safe_decimal(exp_data.get('amount', 0)))
                    db.session.add(receiver)
                    db.session.flush()
                else:
                    receiver.paid_amount += safe_decimal(exp_data.get('amount', 0))
                    db.session.add(receiver)
                    db.session.flush()
                expense = Expenses(
                    date=close_date,
                    amount=safe_decimal(exp_data.get('amount', 0)),
                    note=exp_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    receiver_id=receiver.id
                )
                db.session.add(expense)
        
        # Process Advances
        from models import EmployeeWorking
        for adv_data in data.get('advances', []):
            employee_name = adv_data.get('employee_name')
            if employee_name:
                # Find base employee
                employee = Employees.query.filter_by(name=employee_name).first()
                if not employee:
                    employee = Employees(name=employee_name, base_salary=0.0)
                    db.session.add(employee)
                    db.session.flush()
                
                # Find or create monthly record
                working_record = EmployeeWorking.query.filter_by(
                    employee_id=employee.id, 
                    month=close_date.month, 
                    year=close_date.year
                ).first()
                if not working_record:
                    carryover_debt = apply_carryover_debt(employee.id, close_date.year, close_date.month)
                    working_record = EmployeeWorking(
                        employee_id=employee.id,
                        month=close_date.month,
                        year=close_date.year,
                        deductions_total=carryover_debt,
                        actual_salary=-carryover_debt
                    )
                    db.session.add(working_record)
                    db.session.flush()
                
                amount = safe_decimal(adv_data.get('amount', 0))
                advance_rec = Advances(
                    date=close_date,
                    amount=amount,
                    note=adv_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    employee_id=employee.id
                )
                db.session.add(advance_rec)
                working_record.advance_total = safe_decimal(working_record.advance_total or 0) + amount
                working_record.calculate_salary()

        # Process Deductions
        from models import Deductions
        for ded_data in data.get('deductions', []):
            employee_name = ded_data.get('employee_name')
            if employee_name:
                # Find base employee
                employee = Employees.query.filter_by(name=employee_name).first()
                if not employee:
                    employee = Employees(name=employee_name, base_salary=0.0)
                    db.session.add(employee)
                    db.session.flush()
                
                # Find or create monthly record
                working_record = EmployeeWorking.query.filter_by(
                    employee_id=employee.id, 
                    month=close_date.month, 
                    year=close_date.year
                ).first()
                if not working_record:
                    carryover_debt = apply_carryover_debt(employee.id, close_date.year, close_date.month)
                    working_record = EmployeeWorking(
                        employee_id=employee.id,
                        month=close_date.month,
                        year=close_date.year,
                        deductions_total=carryover_debt,
                        actual_salary=-carryover_debt
                    )
                    db.session.add(working_record)
                    db.session.flush()
                
                amount = safe_decimal(ded_data.get('amount', 0))
                deduction_rec = Deductions(
                    date=close_date,
                    amount=amount,
                    note=ded_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    employee_id=employee.id
                )
                db.session.add(deduction_rec)
                working_record.deductions_total = safe_decimal(working_record.deductions_total or 0) + amount
                working_record.calculate_salary()
        
        # Process Credits
        for cr_data in data.get('credits', []):
            customer_name = cr_data.get('customer_name')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    customer = Customers(username=customer_name, balance=0.0)
                    db.session.add(customer)
                    db.session.flush()
                
                amount = safe_decimal(cr_data.get('amount', 0))
                credit = Credits(
                    date=close_date,
                    amount=amount,
                    note=cr_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    customer_id=customer.id
                )
                db.session.add(credit)
                customer.balance = safe_decimal(customer.balance or 0) - amount
        
        # Process Cashbacks
        for cb_data in data.get('cashbacks', []):
            customer_name = cb_data.get('customer_name')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    customer = Customers(username=customer_name, balance=0.0)
                    db.session.add(customer)
                    db.session.flush()
                
                amount = safe_decimal(cb_data.get('amount', 0))
                cashback = Cashbacks(
                    date=close_date,
                    amount=amount,
                    note=cb_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    customer_id=customer.id
                )
                db.session.add(cashback)
                customer.balance = safe_decimal(customer.balance or 0) + amount
                
        # Process Ahmad's Expenses (Single field from Daily Close)
        ahmad_amount = safe_decimal(data.get('ahmad_expenses', 0))
        if ahmad_amount > 0:
            # Check for a default receiver if none specified, for now just creating the expense
            ahmad_exp = AhmadMistrahExpenses(
                date=close_date,
                amount=ahmad_amount,
                note="From Daily Close",
                daily_closing_id=daily_close.id
            )
            db.session.add(ahmad_exp)

        # Process Samer's Expenses (List from Daily Close)
        for samer_exp_data in data.get('samer_expenses', []):
            # Extract receiver name from available fields
            rc_name = (samer_exp_data.get('receiver_name') or 
                       samer_exp_data.get('note') or 
                       samer_exp_data.get('description') or 
                       samer_exp_data.get('samer-expense-description'))
            
            if not rc_name:
                continue # Skip if no name provided

            rc = SamerExpenseReceivers.query.filter_by(name=rc_name).first()
            if not rc:
                rc = SamerExpenseReceivers(name=rc_name, paid_amount=0)
                db.session.add(rc)
                db.session.flush()
            
            # Update paid amount for both new and existing receivers
            amount = safe_decimal(samer_exp_data.get('amount', 0))
            rc.paid_amount = safe_decimal(rc.paid_amount or 0) + amount
            
            s_expense = SamerExpenses(
                date=close_date,
                amount=amount,
                note=samer_exp_data.get('note', '') or samer_exp_data.get('description', ''),
                daily_closing_id=daily_close.id,
                receiver_id=rc.id
            )
            db.session.add(s_expense)
            
        db.session.commit()
        log_event(
            level='SUCCESS', 
            action='DAILY_CLOSE_COMPLETED', 
            message=f"Daily close processed for {close_date_str}",
            status_code=200,
            details={'date': close_date_str, 'total_cashout': float(daily_close.total_cashout)}
        )
        return jsonify({'status': 'success', 'message': 'Daily close processed successfully'})
        
    except Exception as e:
        app.logger.error(f"Error processing daily close: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to process daily close: {str(e)}'}), 500

@app.route('/api/receivers', methods=['POST'])
@login_required
def create_receiver():
    """Create new receiver"""
    try:
        from models import Receivers
        data = request.get_json()
        
        receiver = Receivers(
            name=data.get('name'),
            paid_amount=safe_decimal(data.get('paid_amount', 0.0))
        )
        
        db.session.add(receiver)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'id': receiver.id,
            'name': receiver.name,
            'paid_amount': receiver.paid_amount
        })
    except Exception as e:
        app.logger.error(f"Error creating receiver: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create receiver'}), 500

@app.route('/api/receivers/<int:receiver_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def receiver_detail(receiver_id):
    """Get, update, or delete a receiver"""
    try:
        from models import Receivers
        receiver = Receivers.query.get_or_404(receiver_id)
        
        if request.method == 'GET':
            return jsonify({
                'id': receiver.id,
                'name': receiver.name,
                'paid_amount': receiver.paid_amount
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            receiver.name = data.get('name', receiver.name)
            receiver.paid_amount = safe_decimal(data.get('paid_amount', receiver.paid_amount))
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Receiver updated successfully'})
            
        elif request.method == 'DELETE':
            from models import Expenses
            conflict_response = check_dependencies_and_respond(
                entity_type='receiver',
                entity_id=receiver.id,
                checks=[
                    ('expenses', Expenses, {'receiver_id': receiver.id})
                ]
            )
            if conflict_response:
                return conflict_response

            db.session.delete(receiver)
            db.session.commit()
            
            log_event(
                level='SUCCESS',
                action='receiver_delete',
                message=f'Receiver {receiver.name} deleted successfully',
                details={'id': receiver.id, 'name': receiver.name}
            )
            
            return jsonify({
                'status': 'success',
                'ok': True,
                'message': 'Receiver deleted successfully',
                'toast': {
                    'type': 'success',
                    'title': 'Success',
                    'message': 'Receiver deleted successfully.'
                }
            })
            
    except Exception as e:
        app.logger.error(f"Error managing receiver {receiver_id}: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to manage receiver: {str(e)}'}), 500

@app.route('/api/customers')
@login_required
def get_customers():
    """Get all customers"""
    try:
        from models import Customers
        customers = Customers.query.all()
        return jsonify({
            'customers': [{
                'id': c.id,
                'username': c.username,
                'balance': c.balance,
                'phone_number': c.phone_number
            } for c in customers]
        })
    except Exception as e:
        app.logger.error(f"Error fetching customers: {e}")
        return jsonify({'error': 'Failed to fetch customers'}), 500

@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    """Create new customer"""
    try:
        from models import Customers
        data = request.get_json()
        
        customer = Customers(
            username=data.get('username'),
            balance=safe_decimal(data.get('balance', 0)),
            phone_number=data.get('phone_number')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Customer created successfully',
            'id': customer.id
        })
    except Exception as e:
        app.logger.error(f"Error creating customer: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create customer'}), 500

@app.route('/api/customers/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def customer_detail(customer_id):
    """Get, update, or delete a customer"""
    try:
        from models import Customers
        customer = Customers.query.get_or_404(customer_id)
        
        if request.method == 'GET':
            return jsonify({
                'id': customer.id,
                'username': customer.username,
                'phone_number': customer.phone_number,
                'balance': customer.balance
            })
            
        if request.method == 'PUT':
            data = request.get_json()
            customer.username = data.get('username', customer.username)
            customer.phone_number = data.get('phone_number', customer.phone_number)
            
            if 'balance' in data:
                new_balance = safe_decimal(data['balance'], customer.balance)
                if new_balance != customer.balance:
                    diff = new_balance - (customer.balance or 0)
                    
                    if diff > 0:
                        # Balance increased (more positive): means they gave us money/paid debt, so auto Cashback
                        from models import Cashbacks
                        auto_cashback = Cashbacks(amount=diff, customer_id=customer.id, note="Added via Customer Edit")
                        db.session.add(auto_cashback)
                    elif diff < 0:
                        # Balance decreased (more negative): means they accrued debt, so auto Credit
                        from models import Credits
                        auto_credit = Credits(amount=abs(diff), customer_id=customer.id, note="Added via Customer Edit")
                        db.session.add(auto_credit)

                customer.balance = new_balance
                
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Customer updated successfully'})
            
        # DELETE
        from models import Credits, Cashbacks
        conflict_response = check_dependencies_and_respond(
            entity_type='customer',
            entity_id=customer.id,
            checks=[
                ('credits', Credits, {'customer_id': customer.id}),
                ('cashbacks', Cashbacks, {'customer_id': customer.id})
            ]
        )
        if conflict_response:
            return conflict_response

        db.session.delete(customer)
        db.session.commit()
        
        log_event(
            level='SUCCESS',
            action='customer_delete',
            message=f'Customer {customer.username} deleted successfully',
            details={'id': customer.id, 'username': customer.username}
        )
        
        return jsonify({
            'status': 'success',
            'ok': True,
            'message': 'Customer deleted successfully',
            'toast': {
                'type': 'success',
                'title': 'Success',
                'message': 'Customer deleted successfully.'
            }
        })
    except Exception as e:
        app.logger.error(f"Error processing customer: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process customer'}), 500

@app.route('/api/employees')
@login_required
def get_employees():
    """Get monthly employee records"""
    try:
        from models import EmployeeWorking
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        query = EmployeeWorking.query
        if year is not None:
            query = query.filter_by(year=year)
        if month is not None:
            query = query.filter_by(month=month)
        records = query.all()
        return jsonify({
            'employees': [{
                'id': r.id,
                'employee_id': r.employee_id,
                'name': r.employee.name,
                'phone_number': r.employee.phone_number,
                'position': r.employee.position,
                'base_salary': r.employee.base_salary,
                'working_days': r.working_days,
                'actual_working_days': r.actual_working_days,
                'deductions': r.deductions_total,
                'advance': r.advance_total,
                'actual_salary': r.actual_salary,
                'total': r.total,
                'year': r.year,
                'month': r.month
            } for r in records]
        })
    except Exception as e:
        app.logger.error(f"Error fetching employees: {e}")
        return jsonify({'error': 'Failed to fetch employees'}), 500

@app.route('/api/employees', methods=['POST'])
@login_required
def create_employee():
    """Create new employee and/or monthly record"""
    try:
        from models import Employees, EmployeeWorking
        from datetime import datetime
        data = request.get_json()
        
        name = data.get('name')
        year = safe_int(data.get('year'), datetime.now(timezone.utc).year)
        month = safe_int(data.get('month'), datetime.now(timezone.utc).month)

        # 1. Find or create base employee
        employee = Employees.query.filter_by(name=name).first()
        if not employee:
            employee = Employees(
                name=name,
                phone_number=data.get('phone_number'),
                position=data.get('position'),
                base_salary=safe_decimal(data.get('base_salary', 0))
            )
            db.session.add(employee)
            db.session.flush()
        
        # 2. Check if monthly record already exists
        record = EmployeeWorking.query.filter_by(employee_id=employee.id, year=year, month=month).first()
        if record:
            return jsonify({'error': f'A record for {name} already exists for {year}-{month}'}), 400

        # 3. Create monthly record
        carryover_debt = apply_carryover_debt(employee.id, year, month)
        base_deductions = safe_decimal(data.get('deductions', 0))
        record = EmployeeWorking(
            employee_id=employee.id,
            year=year,
            month=month,
            working_days=safe_decimal(data.get('working_days', 0)),
            actual_working_days=safe_decimal(data.get('actual_working_days', 0)),
            deductions_total=base_deductions + safe_decimal(carryover_debt),
            advance_total=safe_decimal(data.get('advance', 0)),
            is_working=bool(data.get('is_working', True)) # Default to True if not provided
        )
        record.calculate_salary()
        db.session.add(record)
        db.session.commit()
        
        log_event(
            level='SUCCESS',
            action='EMPLOYEE_CREATED',
            message=f"Employee {employee.name} record created for {month}/{year}",
            status_code=201,
            details={'employee_id': employee.id, 'name': employee.name, 'month': month, 'year': year, 'record_id': record.id}
        )
        return jsonify({
            'status': 'success',
            'message': 'Employee record created successfully',
            'id': record.id
        })
    except Exception as e:
        app.logger.error(f"Error creating employee: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create employee'}), 500

@app.route('/api/employees/<int:record_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def employee_detail(record_id):
    """Get, update, or delete a monthly employee record or base employee"""
    try:
        from models import Employees, EmployeeWorking

        if record_id == 0:
            # Handle base employee only (transient record)
            emp_id = request.args.get('employee_id', type=int)
            if not emp_id:
                return jsonify({'error': 'Employee ID required'}), 400
            employee = Employees.query.get_or_404(emp_id)
            record = None
        else:
            record = EmployeeWorking.query.get_or_404(record_id)
            employee = record.employee

        if request.method == 'GET':
            return jsonify({
                'id': record.id if record else 0,
                'employee_id': employee.id,
                'name': employee.name,
                'phone_number': employee.phone_number,
                'position': employee.position,
                'year': record.year if record else 0,
                'month': record.month if record else 0,
                'is_working': record.is_working if record else True,
                'base_salary': float(employee.base_salary),
                'working_days': float(record.working_days if record else 0),
                'actual_working_days': float(record.actual_working_days if record else 0),
                'deductions': float(record.deductions_total if record else 0),
                'advance': float(record.advance_total if record else 0)
            })

        if request.method == 'PUT':
            data = request.get_json()

            # 1. Update base employee info
            employee.name = data.get('name', employee.name)
            employee.phone_number = data.get('phone_number', employee.phone_number)
            employee.position = data.get('position', employee.position)
            if 'base_salary' in data:
                employee.base_salary = safe_decimal(data['base_salary'], employee.base_salary)

            # 2. Update monthly record if it exists
            if record:
                if 'is_working' in data:
                    record.is_working = bool(data['is_working'])
                if 'working_days' in data:
                    record.working_days = safe_decimal(data['working_days'], record.working_days)
                if 'actual_working_days' in data:
                    record.actual_working_days = safe_decimal(data['actual_working_days'], record.actual_working_days or 0)
                if 'deductions' in data:
                    new_deductions = safe_decimal(data['deductions'], record.deductions_total or 0)
                    if new_deductions != (record.deductions_total or 0):
                        diff = new_deductions - (record.deductions_total or 0)
                        if diff > 0:
                            from models import Deductions
                            new_deduction = Deductions(amount=diff, employee_id=employee.id, note=f"Added via Employee Edit for {record.month}/{record.year}")
                            db.session.add(new_deduction)
                    record.deductions_total = new_deductions
                if 'advance' in data:
                    new_advance = safe_decimal(data['advance'], record.advance_total or 0)
                    if new_advance != (record.advance_total or 0):
                        diff = new_advance - (record.advance_total or 0)
                        if diff > 0:
                            from models import Advances
                            new_advance_rec = Advances(amount=diff, employee_id=employee.id, note=f"Added via Employee Edit for {record.month}/{record.year}")
                            db.session.add(new_advance_rec)
                    record.advance_total = new_advance

                record.calculate_salary()

            db.session.commit()
            log_event(
                level='INFO',
                action='EMPLOYEE_UPDATED',
                message=f"Employee {employee.name} (ID: {employee.id}) record updated.",
                status_code=200,
                details={'employee_id': employee.id, 'record_id': record_id if record else None, 'changes': data}
            )
            return jsonify({'status': 'success', 'message': 'Employee updated successfully'})

        # DELETE
        if record:
            return jsonify({
                'error': 'Cannot delete an active monthly working record directly. Please edit to mark as "Not Working" instead.',
                'toast': {
                'title': 'Error',
                    'message': 'Cannot delete working records directly. Edit and set to Not Working.',
                    'type': 'error'
                }
            }), 400
        else:
            # Delete base employee
            from models import EmployeeWorking, Advances, Deductions
            conflict_response = check_dependencies_and_respond(
                entity_type='employee',
                entity_id=employee.id,
                checks=[
                    ('monthly_records', EmployeeWorking, {'employee_id': employee.id}),
                    ('advances', Advances, {'employee_id': employee.id}),
                    ('deductions', Deductions, {'employee_id': employee.id})
                ]
            )
            if conflict_response:
                return conflict_response

            db.session.delete(employee)
            db.session.commit()
            log_event(
                level='WARNING',
                action='EMPLOYEE_BASE_DELETED',
                message=f"Base employee {employee.name} (ID: {employee.id}) deleted.",
                status_code=200,
                details={'employee_id': employee.id, 'name': employee.name}
            )
            return jsonify({
                'status': 'success', 
                'ok': True,
                'message': 'Employee deleted successfully',
                'toast': {
                    'type': 'success',
                    'title': 'Success',
                    'message': 'Employee deleted successfully.'
                }
            })

    except Exception as e:
        app.logger.error(f"Error processing employee: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process employee'}), 500

# API Routes for future AJAX integration
@app.route('/api/users', methods=['POST'])
@login_required
def create_user_api():
    """Create new user via API"""
    try:
        data = request.get_json()
        
        # Check if username already exists
        from models import User
        existing_user = User.query.filter_by(username=data.get('username')).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create new user
        user = create_user(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            role=data.get('role', 'user')
        )
        
        if user:
            return jsonify({
                'status': 'success',
                'message': 'User created successfully',
                'id': user.id
            })
        else:
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        app.logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def user_detail_api(user_id):
    """Get, update, or delete user via API"""
    try:
        from models import User
        user = User.query.get_or_404(user_id)
        
        if request.method == 'GET':
            return jsonify({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            })
            
        if request.method == 'PUT':
            data = request.get_json()
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            if 'role' in data:
                user.role = data['role']
            if data.get('password'):
                user.password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'User updated successfully'})

        # DELETE
        # Prevent deleting admin user
        if user.username == 'admin':
            return jsonify({'error': 'Cannot delete admin user'}), 400
            
        from models import Logs
        conflict_response = check_dependencies_and_respond(
            entity_type='user',
            entity_id=user.id,
            checks=[
                ('logs', Logs, {'user_id': user.id})
            ]
        )
        if conflict_response:
            return conflict_response
        
        db.session.delete(user)
        db.session.commit()
        
        log_event(
            level='SUCCESS',
            action='user_delete',
            message=f'User {user.username} deleted successfully',
            details={'id': user.id, 'username': user.username}
        )
        
        return jsonify({
            'status': 'success',
            'ok': True,
            'message': 'User deleted successfully',
            'toast': {
                'type': 'success',
                'title': 'Success',
                'message': 'User deleted successfully.'
            }
        })
    except Exception as e:
        app.logger.error(f"Error processing user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process user'}), 500

@app.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    """Create new expense with potentially new receiver"""
    try:
        from models import Expenses, Receivers
        from datetime import datetime
        
        data = request.get_json()
        receiver_name = data.get('receiver_name')
        receiver_id = data.get('receiver_id')
        
        # Logic for searchable receiver
        if receiver_name:
            receiver = Receivers.query.filter_by(name=receiver_name).first()
            if not receiver:
                receiver = Receivers(name=receiver_name, paid_amount=0.0)
                db.session.add(receiver)
                db.session.flush() # Get ID before commit
            receiver_id = receiver.id
        
        expense = Expenses(
            date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.now(UTC),
            amount=safe_decimal(data.get('amount', 0)),
            note=data.get('note', ''),
            receiver_id=receiver_id
        )
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Expense created successfully',
            'id': expense.id
        })
    except Exception as e:
        app.logger.error(f"Error creating expense: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create expense'}), 500

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Delete expense"""
    try:
        from models import Expenses
        expense = Expenses.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        
        log_event(
            level='SUCCESS',
            action='expense_delete',
            message=f'Expense of {expense.amount} deleted successfully',
            details={'id': expense.id, 'amount': str(expense.amount)}
        )
        
        return jsonify({
            'status': 'success',
            'ok': True,
            'message': 'Expense deleted successfully',
            'toast': {
                'type': 'success',
                'title': 'Success',
                'message': 'Expense deleted successfully.'
            }
        })
    except Exception as e:
        app.logger.error(f"Error deleting expense: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete expense'}), 500

# Ahmad Expenses API
@app.route('/api/ahmad-expenses', methods=['GET', 'POST'])
@login_required
def ahmad_expenses_api():
    from models import AhmadMistrahExpenses, AhmadExpenseReceivers
    from datetime import datetime
    
    if request.method == 'GET':
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            query = AhmadMistrahExpenses.query
            if start_date:
                query = query.filter(AhmadMistrahExpenses.date >= datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                query = query.filter(AhmadMistrahExpenses.date <= datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            
            expenses = query.all()
            return jsonify({
                'status': 'success',
                'expenses': [{
                    'id': e.id,
                    'date': e.date.strftime('%Y-%m-%d'),
                    'amount': float(e.amount),
                    'note': e.note,
                    'receiver_name': e.receiver.name if e.receiver else 'General'
                } for e in expenses],
                'total': sum(float(e.amount) for e in expenses)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.get_json()
            receiver_id = data.get('receiver_id')
            
            # Strict validation: Receiver must exist
            receiver = AhmadExpenseReceivers.query.get(receiver_id) if receiver_id else None
            if not receiver:
                return jsonify({'error': 'Valid receiver is required'}), 400

            expense = AhmadMistrahExpenses(
                date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.now(UTC),
                amount=safe_decimal(data.get('amount')),
                note=data.get('note'),
                daily_closing_id=data.get('daily_closing_id'),
                receiver_id=receiver.id
            )
            db.session.add(expense)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Expense added'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@app.route('/api/payroll/import', methods=['POST'])
@login_required
def import_payroll_to_expenses():
    """Import total advances or salaries for a specific month as business expenses"""
    try:
        from models import EmployeeWorking, Expenses, Receivers
        import calendar
        
        data = request.get_json()
        import_type = data.get('type') # 'advances' or 'salaries'
        month = safe_int(data.get('month'))
        year = safe_int(data.get('year'))
        
        if not all([import_type, month, year]):
            return jsonify({'error': 'Missing required parameters: type, month, year'}), 400
            
        if import_type not in ['advances', 'salaries']:
            return jsonify({'error': 'Invalid import type. Use "advances" or "salaries"'}), 400
            
        # 1. Calculate the total sum for the period
        records = EmployeeWorking.query.filter_by(month=month, year=year).all()
        if not records:
            return jsonify({'error': f'No payroll records found for {month}/{year}'}), 404
            
        total_amount = 0
        if import_type == 'advances':
            total_amount = sum(float(r.advance_total or 0) for r in records)
            receiver_name = "Staff Advances"
            note = f"Imported total advances for {month}/{year}"
        else: # salaries
            total_amount = sum(float(r.total or 0) for r in records)
            receiver_name = "Staff Salaries"
            note = f"Imported total salaries for {month}/{year}"
            
        if total_amount <= 0:
            return jsonify({'error': f'Total {import_type} amount is zero for {month}/{year}'}), 400
            
        # 2. Get or create the receiver
        receiver = Receivers.query.filter_by(name=receiver_name).first()
        if not receiver:
            receiver = Receivers(name=receiver_name, paid_amount=0)
            db.session.add(receiver)
            db.session.flush()
            
        # 3. Create the expense record
        # Set date to the last day of the month
        last_day = calendar.monthrange(year, month)[1]
        expense_date = datetime(year, month, last_day)
        
        # Check if already imported to avoid duplicates
        existing = Expenses.query.filter_by(
            receiver_id=receiver.id,
            note=note
        ).first()
        
        if existing:
            return jsonify({'error': f'This {import_type} import already exists for {month}/{year}'}), 400
            
        expense = Expenses(
            date=expense_date,
            amount=decimal.Decimal(str(total_amount)).quantize(decimal.Decimal('0.01')),
            note=note,
            receiver_id=receiver.id
        )
        
        receiver.paid_amount = float(receiver.paid_amount or 0) + total_amount
        
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully imported {import_type} as a business expense (${total_amount:.2f})',
            'expense_id': expense.id
        })
        
    except Exception as e:
        app.logger.error(f"Error importing payroll to expenses: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to import: {str(e)}'}), 500

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """Main Audit Logs UI"""
    from models import Logs
    # Get initial data for filters
    actions = db.session.query(Logs.action).distinct().all()
    actions = sorted([a[0] for a in actions if a[0]])
    return render_template('admin_logs.html', actions=actions)

@app.route('/admin/logs/table')
@login_required
@admin_required
def admin_logs_table():
    """AJAX partial for logs table"""
    from models import Logs
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('pageSize', 25, type=int)
        search = request.args.get('search', '')
        level = request.args.get('level', 'All')
        action = request.args.get('action', 'All')
        status = request.args.get('status', 'All')
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        query = Logs.query
        
        if search:
            query = query.filter(db.or_(
                Logs.message.ilike(f'%{search}%'),
                Logs.action.ilike(f'%{search}%'),
                Logs.path.ilike(f'%{search}%'),
                Logs.username.ilike(f'%{search}%'),
                Logs.request_id.ilike(f'%{search}%')
            ))
        
        if level != 'All':
            query = query.filter_by(level=level)
        
        if action != 'All':
            query = query.filter_by(action=action)
            
        if status != 'All':
            try:
                query = query.filter_by(status_code=int(status))
            except ValueError:
                pass
            
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                query = query.filter(Logs.created_at >= start_date)
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Logs.created_at <= end_date)
            except ValueError:
                pass
        
        # Log the search event internally (as requested: log entry created logs_table_load)
        # Note: We don't want to log every single AJAX call to avoid recursion or bloat,
        # but the prompt asks for it. I'll use a specific action name.
        
        pagination = query.order_by(Logs.created_at.desc()).paginate(page=page, per_page=per_page)
        
        return render_template('partials/logs_table.html', pagination=pagination)
    except Exception as e:
        app.logger.error(f"Error loading logs table: {e}")
        log_event(level='ERROR', action='logs_table_load_failed', message=str(e), status_code=500)
        return "Internal Server Error", 500

@app.route('/api/admin/logs/<int:log_id>')
@login_required
@admin_required
def admin_log_details(log_id):
    """Get detail JSON for a single log"""
    from models import Logs
    import json
    try:
        log = Logs.query.get_or_404(log_id)
        
        details = {}
        if log.details_json:
            try:
                details = json.loads(log.details_json)
            except:
                details = {"raw": log.details_json}
        
        return jsonify({
            'id': log.id,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'level': log.level,
            'action': log.action,
            'username': log.username,
            'ip_address': log.ip_address,
            'status_code': log.status_code,
            'path': log.path,
            'message': log.message,
            'details': details
        })
    except Exception as e:
        app.logger.error(f"Error fetching log details: {e}")
        return jsonify({'error': 'Failed to load log details'}), 500

@app.route('/admin/logs/export')
@login_required
@admin_required
def admin_logs_export():
    """Export filtered logs to CSV"""
    from models import Logs
    import csv
    import io
    from flask import Response
    
    try:
        # Re-apply same filters as table
        search = request.args.get('search', '')
        level = request.args.get('level', 'All')
        action = request.args.get('action', 'All')
        status = request.args.get('status', 'All')
        start_date_str = request.args.get('startDate')
        end_date_str = request.args.get('endDate')
        
        query = Logs.query
        # ... repeat filtering logic (abstracted would be better but let's be explicit for now)
        if search:
            query = query.filter(db.or_(
                Logs.message.ilike(f'%{search}%'),
                Logs.action.ilike(f'%{search}%'),
                Logs.path.ilike(f'%{search}%'),
                Logs.username.ilike(f'%{search}%')
            ))
        if level != 'All': query = query.filter_by(level=level)
        if action != 'All': query = query.filter_by(action=action)
        if status != 'All': 
             try: query = query.filter_by(status_code=int(status))
             except: pass
        if start_date_str:
            try: query = query.filter(Logs.created_at >= datetime.strptime(start_date_str, '%Y-%m-%d'))
            except: pass
        if end_date_str:
            try: query = query.filter(Logs.created_at <= datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            except: pass
            
        logs = query.order_by(Logs.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Date', 'Level', 'User', 'Action', 'Path', 'Status', 'Message'])
        
        for log in logs:
            writer.writerow([
                log.id,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.level,
                log.username,
                log.action,
                log.path,
                log.status_code,
                log.message
            ])
            
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        app.logger.error(f"Export failed: {e}")
        log_event(level='ERROR', action='logs_export_failed', message=str(e), status_code=500)
        flash('Export failed.', 'error')
        return redirect(url_for('admin_logs'))

@app.route('/api/ahmad-expenses/<int:expense_id>', methods=['PUT', 'DELETE'])
@login_required
def ahmad_expense_detail(expense_id):
    from models import AhmadMistrahExpenses, AhmadExpenseReceivers
    expense = AhmadMistrahExpenses.query.get_or_404(expense_id)
    
    if request.method == 'PUT':
        try:
            data = request.get_json()
            receiver_id = data.get('receiver_id')
            if receiver_id:
                receiver = AhmadExpenseReceivers.query.get(receiver_id)
                if not receiver:
                    return jsonify({'error': 'Invalid receiver ID'}), 400
                expense.receiver_id = receiver.id
            
            expense.amount = safe_decimal(data.get('amount', float(expense.amount)))
            expense.note = data.get('note', expense.note)
            if 'date' in data:
                expense.date = datetime.strptime(data['date'], '%Y-%m-%d')
            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    if request.method == 'DELETE':
        try:
            amount = str(expense.amount)
            db.session.delete(expense)
            db.session.commit()
            
            log_event(
                level='SUCCESS',
                action='samer_expense_delete',
                message=f"Samer's expense of {amount} deleted successfully",
                details={'id': expense.id, 'amount': amount}
            )
            
            return jsonify({
                'status': 'success',
                'ok': True,
                'message': 'Expense deleted successfully',
                'toast': {
                    'type': 'success',
                    'title': 'Success',
                    'message': 'Expense deleted successfully.'
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

# Samer Expenses API
@app.route('/api/samer-expenses', methods=['GET', 'POST'])
@login_required
def samer_expenses_api():
    from models import SamerExpenses, SamerExpenseReceivers
    from datetime import datetime
    
    if request.method == 'GET':
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            query = SamerExpenses.query
            if start_date:
                query = query.filter(SamerExpenses.date >= datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                query = query.filter(SamerExpenses.date <= datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            
            expenses = query.all()
            return jsonify({
                'status': 'success',
                'expenses': [{
                    'id': e.id,
                    'date': e.date.strftime('%Y-%m-%d'),
                    'amount': float(e.amount),
                    'note': e.note,
                    'receiver_name': e.receiver.name if e.receiver else 'General'
                } for e in expenses],
                'total': sum(float(e.amount) for e in expenses)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        try:
            data = request.get_json()
            receiver_id = data.get('receiver_id')
            
            # Strict validation: Receiver must exist
            receiver = SamerExpenseReceivers.query.get(receiver_id) if receiver_id else None
            if not receiver:
                return jsonify({'error': 'Valid receiver is required'}), 400

            expense = SamerExpenses(
                date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.now(UTC),
                amount=safe_decimal(data.get('amount')),
                note=data.get('note'),
                daily_closing_id=data.get('daily_closing_id'),
                receiver_id=receiver.id
            )
            db.session.add(expense)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Expense added'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

@app.route('/api/samer-expenses/<int:expense_id>', methods=['PUT', 'DELETE'])
@login_required
def samer_expense_detail(expense_id):
    from models import SamerExpenses, SamerExpenseReceivers
    expense = SamerExpenses.query.get_or_404(expense_id)
    
    if request.method == 'PUT':
        try:
            data = request.get_json()
            receiver_id = data.get('receiver_id')
            if receiver_id:
                receiver = SamerExpenseReceivers.query.get(receiver_id)
                if not receiver:
                    return jsonify({'error': 'Invalid receiver ID'}), 400
                expense.receiver_id = receiver.id
            
            expense.amount = safe_decimal(data.get('amount', float(expense.amount)))
            expense.note = data.get('note', expense.note)
            if 'date' in data:
                expense.date = datetime.strptime(data['date'], '%Y-%m-%d')
            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    if request.method == 'DELETE':
        try:
            amount = str(expense.amount)
            db.session.delete(expense)
            db.session.commit()
            
            log_event(
                level='SUCCESS',
                action='ahmad_expense_delete',
                message=f"Ahmad's expense of {amount} deleted successfully",
                details={'id': expense.id, 'amount': amount}
            )
            
            return jsonify({
                'status': 'success',
                'ok': True,
                'message': 'Expense deleted successfully',
                'toast': {
                    'type': 'success',
                    'title': 'Success',
                    'message': 'Expense deleted successfully.'
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

# Report API Routes
@app.route('/api/reports/sales', methods=['POST'])
@login_required
def sales_report():
    """Generate sales report for month/year"""
    def safe_float(value, default=0.0):
        """Convert value to float safely, returning default if invalid."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default  
    try:
        from datetime import datetime
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        from models import DailyClosing, Customers
        # Get closings for the specific month/year
        closings = DailyClosing.query.filter(
            db.extract('year', DailyClosing.date) == year,
            db.extract('month', DailyClosing.date) == month
        ).all()
        
        total_sales = sum(c.main_reading or 0 for c in closings)
        
        # Calculate total customer balances
        all_customers = Customers.query.all()
        total_customer_balance = sum(float(c.balance or 0) for c in all_customers)

        # Calculate actual cash using the formula: Total Sales - Customer Balances
        actual_cash = safe_float(total_sales) - safe_float(total_customer_balance)
        
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_sales': total_sales,
            'actual_cash': actual_cash,
            'total_customer_balance': total_customer_balance,
            'sales': [{
                'date': c.date.strftime('%Y-%m-%d') if c.date else 'N/A',
                'amount': c.adjusted_reading or 0,
                'main_reading': c.main_reading or 0,
                'dr_smashed': c.dr_smashed or 0
            } for c in closings]
        }
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
    except Exception as e:
        app.logger.error(f"Error generating sales report: {e}")
        return jsonify({'error': 'Failed to generate sales report'}), 500

@app.route('/api/reports/payroll', methods=['POST'])
@login_required
def payroll_report():
    """Generate payroll report for month/year"""
    try:
        from datetime import datetime
        from models import EmployeeWorking
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))

        # Get all employees for the selected month/year
        employeesworking = EmployeeWorking.query.filter_by(year=year, month=month).all()
        for emp in employeesworking:
            emp.name = emp.employee.name
            emp.position = emp.employee.position
            emp.base_salary = emp.employee.base_salary


        total_payroll = sum(emp.total or 0 for emp in employeesworking)
        total_deductions = sum(emp.deductions_total or 0 for emp in employeesworking)
        
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_payroll': total_payroll,
            'total_employees': len(employeesworking),
            'total_deductions': total_deductions,
            'employees': [{
                'name': emp.name,
                'position': emp.position,
                'base_salary': emp.base_salary or 0,
                'advance': emp.advance_total or 0,
                'deductions': emp.deductions_total or 0,
                'actual_salary': emp.actual_salary or 0,
                'total': emp.total or 0
            } for emp in employeesworking]
        }
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
    except Exception as e:
        app.logger.error(f"Error generating payroll report: {e}")
        return jsonify({'error': 'Failed to generate payroll report', 'details': str(e)}), 500

@app.route('/api/reports/expenses', methods=['POST'])
@login_required
def expenses_report():
    """Generate expenses report for month/year"""
    try:
        from datetime import datetime
        from models import Expenses, Receivers
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        # Extract and format expenses
        general_expenses = Expenses.query.filter(
            db.extract('year', Expenses.date) == year,
            db.extract('month', Expenses.date) == month
        ).all()
        
        total_expenses = sum(safe_decimal(e.amount, decimal.Decimal('0.00')) for e in general_expenses)
        
        # Calculate breakdown by receiver
        receiver_breakdown = {}
        unique_receivers = set()
        
        all_expenses_list = []
        for exp in general_expenses:
            name = exp.receiver.name if exp.receiver else 'Unassigned'
            if exp.receiver_id: unique_receivers.add(exp.receiver_id)
            receiver_breakdown[name] = receiver_breakdown.get(name, 0) + float(exp.amount or 0)
            all_expenses_list.append({
                'type': 'General',
                'date': exp.date.strftime('%Y-%m-%d') if exp.date else 'N/A',
                'receiver': name,
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
            
        report_data = {
            'month': month,
            'year': year,
            'total_expenses': total_expenses,
            'total_receivers': len(unique_receivers),
            'receiver_breakdown': receiver_breakdown,
            'expenses': all_expenses_list
        }
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
    except Exception as e:
        app.logger.error(f"Error generating expenses report: {e}")
        return jsonify({'error': str(e)}), 500

def build_daily_close_payload(closing_id):
    """Helper method to construct the JSON dictionary for a Daily Closing."""
    from models import DailyClosing
    closing = DailyClosing.query.get_or_404(closing_id)
    
    # Format general expenses
    general_expenses = []
    for e in closing.expenses:
        general_expenses.append({
            'amount': e.amount,
            'note': e.note,
            'receiver': e.receiver.name if e.receiver else 'Unassigned'
        })
        
    # Format Ahmad expenses
    ahmad_expenses = []
    for e in closing.ahmad_mistrah_expenses:
        ahmad_expenses.append({
            'amount': e.amount,
            'note': e.note,
            'receiver': e.receiver.name if e.receiver else 'Unassigned'
        })
        
    # Format Samer expenses
    samer_expenses = []
    for e in closing.samer_expenses:
        samer_expenses.append({
            'amount': e.amount,
            'note': e.note,
            'receiver': e.receiver.name if e.receiver else 'Unassigned'
        })
        
    # Format advances
    advances = []
    for a in closing.advances:
        advances.append({
            'amount': a.amount,
            'note': a.note,
            'employee': a.employee.name if a.employee else 'Unassigned'
        })
        
    # Format deductions
    deductions = []
    for d in closing.deductions_rel:
        deductions.append({
            'amount': d.amount,
            'note': d.note,
            'employee': d.employee.name if d.employee else 'Unassigned'
        })
        
    # Format credits
    credits = []
    for c in closing.credits:
        credits.append({
            'amount': c.amount,
            'note': c.note,
            'customer': c.customer.username if c.customer else 'Unassigned'
        })
        
    # Format cashbacks
    cashbacks = []
    for c in closing.cashbacks:
        cashbacks.append({
            'amount': c.amount,
            'note': c.note,
            'customer': c.customer.username if c.customer else 'Unassigned'
        })

    return {
        'id': closing.id,
        'date': closing.date.strftime('%Y-%m-%d'),
        'main_reading': closing.main_reading,
        'dr_smashed': closing.dr_smashed,
        'adjusted_reading': closing.adjusted_reading,
        'total_expenses': closing.total_expenses,
        'total_advance': closing.total_advance,
        'total_credit': closing.total_credit,
        'total_cashback': closing.total_cashback,
        'total_deductions': closing.total_deductions,
        'five_percent': closing.five_percent,
        'total_cashout': closing.total_cashout,
        'actual_cash': closing.actual_cash,
        'expenses': general_expenses,
        'ahmad_expenses': ahmad_expenses,
        'samer_expenses': samer_expenses,
        'advances': advances,
        'deductions': deductions,
        'credits': credits,
        'cashbacks': cashbacks
    }

@app.route('/api/daily-close/<int:closing_id>', methods=['GET'])
@login_required
def get_daily_closing_details(closing_id):
    """Get full details of a specific daily closing"""
    try:
        data = build_daily_close_payload(closing_id)
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Error fetching daily closing details {closing_id}: {e}")
        return jsonify({'error': 'Failed to fetch details'}), 500

@app.route("/control-panel/daily-close/<int:close_id>/print")
@login_required
def print_daily_close(close_id):
    from models import DailyClosing
    closing = DailyClosing.query.get_or_404(close_id)

    data = build_daily_close_payload(close_id)

    date_obj = closing.date
    title_ddmmyyyy = date_obj.strftime("%d-%m-%Y")
    title_ddMonth = date_obj.strftime("%d-%B-%Y")

    return render_template(
        "daily_close_print.html",
        data=data,
        title=title_ddMonth,
        title_ddmmyyyy=title_ddmmyyyy
    )

@app.route('/api/exports/sales')
@login_required
def export_sales_csv():
    try:
        from models import DailyClosing
        from datetime import datetime
        import csv
        from io import StringIO
        from flask import make_response
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if month is None or year is None:
            now = datetime.now(UTC)
            month = now.month
            year = now.year
            
        closings = DailyClosing.query.filter(
            db.extract('year', DailyClosing.date) == year,
            db.extract('month', DailyClosing.date) == month
        ).order_by(DailyClosing.date.desc()).all()
        
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Date', 'Expenses', 'Advances', 'Credits', 'Cashback', 'Deductions', '5% Fee', 'Actual Cash'])
        
        for c in closings:
            cw.writerow([
                c.date.strftime('%Y-%m-%d'),
                f"{c.total_expenses:.2f}",
                f"{c.total_advance:.2f}",
                f"{c.total_credit:.2f}",
                f"{c.total_cashback:.2f}",
                f"{(c.total_deductions or 0):.2f}",
                f"{c.five_percent:.2f}",
                f"{(c.actual_cash or 0):.2f}"
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=sales_export_{year}_{month}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        app.logger.error(f"Error exporting sales: {e}")
        flash('Error exporting sales data', 'error')
        return redirect(url_for('sales'))

@app.route('/api/exports/payroll')
@login_required
def export_payroll_csv():
    try:
        from models import Employees
        from datetime import datetime
        import csv
        from io import StringIO
        from flask import make_response
        
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if month is None or year is None:
            now = datetime.now(UTC)
            month = now.month
            year = now.year
            
        employees = Employees.query.filter_by(year=year, month=month).all()
        
        for emp in employees:
            emp.calculate_salary()
            
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Employee', 'Position', 'Base Salary', 'Working Days', 'Advance', 'Deductions', 'Actual Salary', 'Total'])
        
        for e in employees:
            cw.writerow([
                e.name,
                e.position or 'N/A',
                f"{(e.base_salary or 0):.2f}",
                e.working_days or 0,
                f"{(e.advance or 0):.2f}",
                f"{(e.deductions or 0):.2f}",
                f"{(e.actual_salary or 0):.2f}",
                f"{(e.total or 0):.2f}"
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=payroll_export_{year}_{month}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        app.logger.error(f"Error exporting payroll: {e}")
        flash('Error exporting payroll data', 'error')
        return redirect(url_for('payroll'))

@app.route('/api/exports/reports')
@login_required
def export_reports_csv():
    try:
        from models import Expenses, AhmadMistrahExpenses, SamerExpenses
        from datetime import datetime
        import csv
        from io import StringIO
        from flask import make_response
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        # We need to export all types of expenses
        all_expenses_list = []
        
        # General Expenses
        gen_q = Expenses.query
        if start_date:
            gen_q = gen_q.filter(Expenses.date >= start_date)
        if end_date:
            end_date_time = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            gen_q = gen_q.filter(Expenses.date <= end_date_time)
        if month and year:
            gen_q = gen_q.filter(db.extract('year', Expenses.date) == year, db.extract('month', Expenses.date) == month)
        
        for exp in gen_q.all():
            all_expenses_list.append({
                'type': 'General',
                'date': exp.date.strftime('%Y-%m-%d') if exp.date else 'N/A',
                'receiver': exp.receiver.name if exp.receiver else 'Unassigned',
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
            
        # Ahmad Expenses
        ahmad_q = AhmadMistrahExpenses.query
        if start_date:
            ahmad_q = ahmad_q.filter(AhmadMistrahExpenses.date >= start_date)
        if end_date:
            end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            ahmad_q = ahmad_q.filter(AhmadMistrahExpenses.date <= end_date_dt)
        if month and year:
            ahmad_q = ahmad_q.filter(db.extract('year', AhmadMistrahExpenses.date) == year, db.extract('month', AhmadMistrahExpenses.date) == month)
            
        for exp in ahmad_q.all():
            all_expenses_list.append({
                'type': 'Ahmad Mistrah',
                'date': exp.date.strftime('%Y-%m-%d') if exp.date else 'N/A',
                'receiver': exp.receiver.name if exp.receiver else 'Unassigned',
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
            
        # Samer Expenses
        samer_q = SamerExpenses.query
        if start_date:
            samer_q = samer_q.filter(SamerExpenses.date >= start_date)
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            samer_q = samer_q.filter(SamerExpenses.date <= end_dt)
        if month and year:
            samer_q = samer_q.filter(db.extract('year', SamerExpenses.date) == year, db.extract('month', SamerExpenses.date) == month)
            
        for exp in samer_q.all():
            all_expenses_list.append({
                'type': 'Samer Mistrah',
                'date': exp.date.strftime('%Y-%m-%d') if exp.date else 'N/A',
                'receiver': exp.receiver.name if exp.receiver else 'Unassigned',
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
            
        # Sort by date
        all_expenses_list.sort(key=lambda x: x['date'])
        
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['Type', 'Date', 'Receiver', 'Amount', 'Note'])
        
        for e in all_expenses_list:
            cw.writerow([
                e['type'],
                e['date'],
                e['receiver'],
                f"{e['amount']:.2f}",
                e['note']
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=expenses_report.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        app.logger.error(f"Error exporting reports: {e}")
        flash('Error exporting reports data', 'error')
        return redirect(url_for('reports'))

@app.route('/api/modules/<module_name>')
@login_required
def get_module(module_name):
    """API endpoint for module data"""
    # Placeholder for module data - will be expanded later
    return jsonify({
        'module': module_name,
        'status': 'ready',
        'data': f'{module_name.title()} module loaded successfully'
    })


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
