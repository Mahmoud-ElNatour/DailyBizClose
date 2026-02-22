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

def safe_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == '':
            return default
        return float(value)
    except (ValueError, TypeError):
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

def create_user(username, email, password):
    """Create a new user"""
    try:
        from models import User
       
        user = User(
            username=username,
            email=email,
            password_hash=hashlib.sha256(password.encode()).hexdigest()
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

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    try:
        import models  # noqa: F401
    except ImportError:
        pass  # Models file doesn't exist yet
    db.create_all()

# Create admin user if it doesn't exist
with app.app_context():
    try:
        from models import User
        if not User.query.filter_by(username='admin').first():
            create_user("admin", "admin@admin.com", "admin")
    except Exception as e:
        app.logger.error(f"Error creating admin user: {e}")
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
                app.logger.debug(f"User logged in successfully: {user.username}")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
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
def employees():
    """Employees page - show available years"""
    try:
        from models import Employees, db
        from datetime import datetime
        years = db.session.query(db.func.distinct(Employees.year)).order_by(Employees.year.desc()).all()
        years = [y[0] for y in years]
        current_year = datetime.now(UTC).year
        current_month = datetime.now(UTC).month
        return render_template('employees_years.html', years=years,
                               current_year=current_year, current_month=current_month)
    except Exception as e:
        app.logger.error(f"Error loading employees: {e}")
        flash('Error loading employees data', 'error')
        from datetime import datetime
        dt = datetime.now(UTC)
        return render_template('employees_years.html', years=[],
                               current_year=dt.year, current_month=dt.month)


@app.route('/control-panel/employees/<int:year>')
@login_required
def employees_months(year):
    """Show months for a given year"""
    try:
        from models import Employees, db
        import calendar
        months = db.session.query(db.func.distinct(Employees.month)).filter_by(year=year).order_by(Employees.month).all()
        months = [(m[0], calendar.month_name[m[0]]) for m in months]
        return render_template('employees_months.html', year=year, months=months)
    except Exception as e:
        app.logger.error(f"Error loading employee months: {e}")
        flash('Error loading employees data', 'error')
        return render_template('employees_months.html', year=year, months=[])


@app.route('/control-panel/employees/<int:year>/<int:month>')
@login_required
def employees_list(year, month):
    """Show employees for specific month and year"""
    try:
        from models import Employees
        import calendar
        employees = Employees.query.filter_by(year=year, month=month).all()
        month_name = calendar.month_name[month]
        return render_template('employees.html', employees=employees, year=year, month=month, month_name=month_name)
    except Exception as e:
        app.logger.error(f"Error loading employees: {e}")
        flash('Error loading employees data', 'error')
        return render_template('employees.html', employees=[], year=year, month=month, month_name='')

@app.route('/control-panel/customers')
@login_required
def customers():
    """Customers management page"""
    try:
        from models import Customers
        customers = Customers.query.all()
        return render_template('customers.html', customers=customers)
    except Exception as e:
        app.logger.error(f"Error loading customers: {e}")
        flash('Error loading customers data', 'error')
        return render_template('customers.html', customers=[])

@app.route('/control-panel/users')
@login_required
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
def payroll():
    """Payroll management page"""
    try:
        from models import Employees
        from datetime import datetime
        
        # Get filter parameters
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)

        query = Employees.query
        if year is not None:
            query = query.filter_by(year=year)
        if month is not None:
            query = query.filter_by(month=month)
        employees = query.all()

        return render_template('payroll.html', employees=employees)
    except Exception as e:
        app.logger.error(f"Error loading payroll: {e}")
        flash('Error loading payroll data', 'error')
        return render_template('payroll.html', employees=[])

@app.route('/api/employees/<int:employee_id>/calculate', methods=['POST'])
@login_required
def calculate_employee_payroll(employee_id):
    """Trigger payroll calculation for an employee"""
    try:
        from models import Employees
        employee = Employees.query.get_or_404(employee_id)
        employee.calculate_salary()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Payroll calculated successfully',
            'actual_salary': employee.actual_salary,
            'total': employee.total
        })
    except Exception as e:
        app.logger.error(f"Error calculating payroll: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to calculate payroll'}), 500

@app.route('/payroll/payslip/<int:employee_id>')
@login_required
def generate_payslip_view(employee_id):
    """Render printable payslip for an employee"""
    try:
        from models import Employees, Advances, Deductions
        employee = Employees.query.get_or_404(employee_id)
        
        show_details = True
        details = None
        
        if show_details:
            advances_list = Advances.query.filter_by(employee_id=employee_id).all()
            deductions_list = Deductions.query.filter_by(employee_id=employee_id).all()
            details = {
                'advances': advances_list,
                'deductions': deductions_list
            }
            print(details)
            
        return render_template('payslip.html', employee=employee, show_details=show_details, details=details)
    except Exception as e:
        app.logger.error(f"Error generating payslip: {e}")
        flash('Error generating payslip', 'error')
        return redirect(url_for('payroll'))

@app.route('/control-panel/receivers')
@login_required
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
        
        total = sum(float(e.amount or 0) for e in expenses)
        max_val = max((float(e.amount or 0) for e in expenses), default=0)
        receiver_totals = {}
        for e in expenses:
            name = e.receiver.name if e.receiver else 'General'
            receiver_totals[name] = receiver_totals.get(name, 0) + float(e.amount or 0)
        top_receiver = max(receiver_totals.items(), key=lambda x: x[1], default=('N/A', 0))
        
        stats = {'total': total, 'max': max_val, 'count': len(expenses), 'top_receiver': top_receiver[0], 'top_receiver_amount': top_receiver[1]}
        return render_template('ahmad_expenses.html', expenses=expenses, receivers=receivers, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading Ahmad expenses: {e}")
        return render_template('ahmad_expenses.html', expenses=[], receivers=[], stats={'total': 0, 'max': 0, 'count': 0, 'top_receiver': 'N/A', 'top_receiver_amount': 0})

@app.route('/control-panel/samer-expenses')
@login_required
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
        
        total = sum(float(e.amount or 0) for e in expenses)
        max_val = max((float(e.amount or 0) for e in expenses), default=0)
        receiver_totals = {}
        for e in expenses:
            name = e.receiver.name if e.receiver else 'General'
            receiver_totals[name] = receiver_totals.get(name, 0) + float(e.amount or 0)
        top_receiver = max(receiver_totals.items(), key=lambda x: x[1], default=('N/A', 0))
        
        stats = {'total': total, 'max': max_val, 'count': len(expenses), 'top_receiver': top_receiver[0], 'top_receiver_amount': top_receiver[1]}
        return render_template('samer_expenses.html', expenses=expenses, receivers=receivers, stats=stats)
    except Exception as e:
        app.logger.error(f"Error loading Samer expenses: {e}")
        return render_template('samer_expenses.html', expenses=[], receivers=[], stats={'total': 0, 'max': 0, 'count': 0, 'top_receiver': 'N/A', 'top_receiver_amount': 0})

@app.route('/control-panel/deductions-advances')
@login_required
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
        admin_user = User.query.filter_by(username='admin').first()
        
        if admin_user and admin_user.password_hash == hashlib.sha256(password.encode()).hexdigest():
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
        if not (safe_float(data.get('main_reading', 0)) > 0):
            return jsonify({'error': 'Main Reading is mandatory. Please provide the current counter value.'}), 400

        # Check if already closed for this date
        # For simplicity, we'll allow multiple or overwrite. Let's overwrite?
        # Or just append. Usually, one close per day is expected.
        # existing = DailyClosing.query.filter(db.func.date(DailyClosing.date) == close_date.date()).first()
        
        daily_close = DailyClosing(
            date=close_date,
            main_reading=safe_float(data.get('main_reading', 0)),
            dr_smashed=safe_float(data.get('dr_smashed', 0)),
            adjusted_reading=safe_float(data.get('adjusted_reading', 0)),
            total_expenses=safe_float(data.get('total_expenses', 0)),
            total_advance=safe_float(data.get('total_advance', 0)),
            total_credit=safe_float(data.get('total_credit', 0)),
            total_cashback=safe_float(data.get('total_cashback', 0)),
            total_deductions=safe_float(data.get('total_deductions', 0)),
            five_percent=safe_float(data.get('five_percent', 0)),
            total_cashout=safe_float(data.get('total_cashout', 0)),
            actual_cash=safe_float(data.get('actual_cash', 0))
        )
        db.session.add(daily_close)
        db.session.flush() # Get daily_close.id
        
        # Process Expenses
        for exp_data in data.get('expenses', []):
            receiver_name = exp_data.get('receiver_name')
            if receiver_name:
                receiver = Receivers.query.filter_by(name=receiver_name).first()
                if not receiver:
                    receiver = Receivers(name=receiver_name, paid_amount=safe_float(exp_data.get('amount', 0)))
                    db.session.add(receiver)
                    db.session.flush()
                else:
                    receiver.paid_amount += safe_float(exp_data.get('amount', 0))
                    db.session.add(receiver)
                    db.session.flush()
                expense = Expenses(
                    date=close_date,
                    amount=safe_float(exp_data.get('amount', 0)),
                    note=exp_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    receiver_id=receiver.id
                )
                db.session.add(expense)
        
        # Process Advances
        for adv_data in data.get('advances', []):
            employee_name = adv_data.get('employee_name')
            if employee_name:
                employee = Employees.query.filter_by(name=employee_name, month=close_date.month, year=close_date.year).first()
                if not employee:
                    employee = Employees(name=employee_name, month=close_date.month, year=close_date.year, advance=0.0, deductions=0.0)
                    db.session.add(employee)
                    db.session.flush()
                
                amount = safe_float(adv_data.get('amount', 0))
                advance_rec = Advances(
                    date=close_date,
                    amount=amount,
                    note=adv_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    employee_id=employee.id
                )
                db.session.add(advance_rec)
                employee.advance = safe_float(employee.advance or 0) + amount
                employee.calculate_salary()

        # Process Deductions
        from models import Deductions
        for ded_data in data.get('deductions', []):
            employee_name = ded_data.get('employee_name')
            if employee_name:
                employee = Employees.query.filter_by(name=employee_name, month=close_date.month, year=close_date.year).first()
                if not employee:
                    employee = Employees(name=employee_name, month=close_date.month, year=close_date.year, advance=0.0, deductions=0.0)
                    db.session.add(employee)
                    db.session.flush()
                
                amount = safe_float(ded_data.get('amount', 0))
                deduction_rec = Deductions(
                    date=close_date,
                    amount=amount,
                    note=ded_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    employee_id=employee.id
                )
                db.session.add(deduction_rec)
                employee.deductions = safe_float(employee.deductions or 0) + amount
                employee.calculate_salary()
        
        # Process Credits
        for cr_data in data.get('credits', []):
            customer_name = cr_data.get('customer_name')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    customer = Customers(username=customer_name, balance=0.0)
                    db.session.add(customer)
                    db.session.flush()
                
                amount = safe_float(cr_data.get('amount', 0))
                credit = Credits(
                    date=close_date,
                    amount=amount,
                    note=cr_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    customer_id=customer.id
                )
                db.session.add(credit)
                customer.balance = safe_float(customer.balance or 0) - amount
        
        # Process Cashbacks
        for cb_data in data.get('cashbacks', []):
            customer_name = cb_data.get('customer_name')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    customer = Customers(username=customer_name, balance=0.0)
                    db.session.add(customer)
                    db.session.flush()
                
                amount = safe_float(cb_data.get('amount', 0))
                cashback = Cashbacks(
                    date=close_date,
                    amount=amount,
                    note=cb_data.get('note', ''),
                    daily_closing_id=daily_close.id,
                    customer_id=customer.id
                )
                db.session.add(cashback)
                customer.balance = safe_float(customer.balance or 0) + amount
                
        # Process Ahmad's Expenses (Single field from Daily Close)
        ahmad_amount = safe_float(data.get('ahmad_expenses', 0))
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
            rc_name = samer_exp_data.get('receiver_name') or samer_exp_data.get('description')
            rc = SamerExpenseReceivers.query.filter_by(name=rc_name).first()
            if not rc and rc_name:
                rc = SamerExpenseReceivers(name=rc_name)
                db.session.add(rc)
                db.session.flush()
            
            s_expense = SamerExpenses(
                date=close_date,
                amount=safe_float(samer_exp_data.get('amount', 0)),
                note=samer_exp_data.get('note', '') or samer_exp_data.get('description', ''),
                daily_closing_id=daily_close.id,
                receiver_id=rc.id if rc else None
            )
            db.session.add(s_expense)
            
        db.session.commit()
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
            paid_amount=safe_float(data.get('paid_amount', 0.0))
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
            receiver.paid_amount = safe_float(data.get('paid_amount', receiver.paid_amount))
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Receiver updated successfully'})
            
        elif request.method == 'DELETE':
            db.session.delete(receiver)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Receiver deleted successfully'})
            
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
            balance=safe_float(data.get('balance', 0)),
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
                customer.balance = safe_float(data['balance'], customer.balance)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Customer updated successfully'})
            
        # DELETE
        db.session.delete(customer)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Customer deleted successfully'
        })
    except Exception as e:
        app.logger.error(f"Error processing customer: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process customer'}), 500

@app.route('/api/employees')
@login_required
def get_employees():
    """Get all employees"""
    try:
        from models import Employees
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        query = Employees.query
        if year is not None:
            query = query.filter_by(year=year)
        if month is not None:
            query = query.filter_by(month=month)
        employees = query.all()
        return jsonify({
            'employees': [{
                'id': e.id,
                'name': e.name,
                'phone_number': e.phone_number,
                'position': e.position,
                'base_salary': e.base_salary,
                'working_days': e.working_days,
                'actual_working_days': e.actual_working_days,
                'deductions': e.deductions,
                'advance': e.advance,
                'actual_salary': e.actual_salary,
                'total': e.total,
                'year': e.year,
                'month': e.month
            } for e in employees]
        })
    except Exception as e:
        app.logger.error(f"Error fetching employees: {e}")
        return jsonify({'error': 'Failed to fetch employees'}), 500

@app.route('/api/employees', methods=['POST'])
@login_required
def create_employee():
    """Create new employee"""
    try:
        from models import Employees
        from datetime import datetime
        data = request.get_json()

        employee = Employees(
            name=data.get('name'),
            phone_number=data.get('phone_number'),
            position=data.get('position'),
            year=safe_int(data.get('year'), datetime.now(UTC).year),
            month=safe_int(data.get('month'), datetime.now(UTC).month),
            base_salary=safe_float(data.get('base_salary', 0)),
            working_days=safe_float(data.get('working_days', 0)),
            actual_working_days=safe_float(data.get('actual_working_days', 0)),
            deductions=safe_float(data.get('deductions', 0)),
            advance=safe_float(data.get('advance', 0))
        )
        employee.calculate_salary()
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Employee created successfully',
            'id': employee.id
        })
    except Exception as e:
        app.logger.error(f"Error creating employee: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create employee'}), 500

@app.route('/api/employees/<int:employee_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def employee_detail(employee_id):
    """Get, update, or delete an employee"""
    try:
        from models import Employees
        employee = Employees.query.get_or_404(employee_id)

        if request.method == 'GET':
            return jsonify({
                'id': employee.id,
                'name': employee.name,
                'phone_number': employee.phone_number,
                'position': employee.position,
                'year': employee.year,
                'month': employee.month,
                'base_salary': employee.base_salary,
                'working_days': employee.working_days,
                'actual_working_days': employee.actual_working_days,
                'deductions': employee.deductions,
                'advance': employee.advance,
                'actual_salary': employee.actual_salary,
                'total': employee.total
            })

        if request.method == 'PUT':
            data = request.get_json()
            employee.name = data.get('name', employee.name)
            employee.phone_number = data.get('phone_number', employee.phone_number)
            employee.position = data.get('position', employee.position)
            if 'year' in data: employee.year = safe_int(data['year'], employee.year)
            if 'month' in data: employee.month = safe_int(data['month'], employee.month)
            if 'base_salary' in data: employee.base_salary = safe_float(data['base_salary'], employee.base_salary)
            if 'working_days' in data: employee.working_days = safe_float(data['working_days'], employee.working_days)
            if 'actual_working_days' in data: employee.actual_working_days = safe_float(data['actual_working_days'], employee.actual_working_days)
            if 'deductions' in data: employee.deductions = safe_float(data['deductions'], employee.deductions)
            if 'advance' in data: employee.advance = safe_float(data['advance'], employee.advance)
            employee.calculate_salary()
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Employee updated successfully'})

        # DELETE
        db.session.delete(employee)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Employee deleted successfully'})
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
            password=data.get('password')
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
                'email': user.email
            })
            
        if request.method == 'PUT':
            data = request.get_json()
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            if data.get('password'):
                user.password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'User updated successfully'})

        # DELETE
        # Prevent deleting admin user
        if user.username == 'admin':
            return jsonify({'error': 'Cannot delete admin user'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'User deleted successfully'
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
            amount=safe_float(data.get('amount', 0)),
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
        
        return jsonify({
            'status': 'success',
            'message': 'Expense deleted successfully'
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
                amount=safe_float(data.get('amount')),
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
            
            expense.amount = safe_float(data.get('amount', float(expense.amount)))
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
            db.session.delete(expense)
            db.session.commit()
            return jsonify({'status': 'success'})
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
                amount=safe_float(data.get('amount')),
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
            
            expense.amount = safe_float(data.get('amount', float(expense.amount)))
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
            db.session.delete(expense)
            db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

# Report API Routes
@app.route('/api/reports/sales', methods=['POST'])
@login_required
def sales_report():
    """Generate sales report for month/year"""
    try:
        from datetime import datetime
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        from models import DailyClosing
        # Get closings for the specific month/year
        closings = DailyClosing.query.filter(
            db.extract('year', DailyClosing.date) == year,
            db.extract('month', DailyClosing.date) == month
        ).all()
        
        total_sales = sum(c.adjusted_reading or 0 for c in closings)
        
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_sales': total_sales,
            'total_orders': len(closings),
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
        from models import Employees
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))

        # Get all employees for the selected month/year
        employees = Employees.query.filter_by(year=year, month=month).all()
        
        total_payroll = sum(emp.total or 0 for emp in employees)
        total_deductions = sum(emp.deductions or 0 for emp in employees)
        
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_payroll': total_payroll,
            'total_employees': len(employees),
            'total_deductions': total_deductions,
            'employees': [{
                'name': emp.name,
                'position': emp.position,
                'base_salary': emp.base_salary or 0,
                'advance': emp.advance or 0,
                'deductions': emp.deductions or 0,
                'actual_salary': emp.actual_salary or 0,
                'total': emp.total or 0
            } for emp in employees]
        }
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
    except Exception as e:
        app.logger.error(f"Error generating payroll report: {e}")
        return jsonify({'error': 'Failed to generate payroll report'}), 500

@app.route('/api/reports/expenses', methods=['POST'])
@login_required
def expenses_report():
    """Generate expenses report for a date range or month/year"""
    try:
        from datetime import datetime, timedelta
        from models import Expenses, AhmadMistrahExpenses, SamerExpenses, Receivers
        data = request.get_json()
        
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            # Set end_date to end of day for inclusive datetime filtering
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            month = int(data.get('month', datetime.now(UTC).month))
            year = int(data.get('year', datetime.now(UTC).year))
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Helper to extract and format expenses within date range
        def get_formatted_expenses(model, start, end):
            return model.query.filter(model.date >= start, model.date <= end).all()

        general_expenses = get_formatted_expenses(Expenses, start_date, end_date)
        ahmad_expenses = get_formatted_expenses(AhmadMistrahExpenses, start_date, end_date)
        samer_expenses = get_formatted_expenses(SamerExpenses, start_date, end_date)
        
        total_gen = sum(float(e.amount or 0) for e in general_expenses)
        total_ahmad = sum(float(e.amount or 0) for e in ahmad_expenses)
        total_samer = sum(float(e.amount or 0) for e in samer_expenses)
        
        # Calculate breakdown by receiver for all types
        receiver_breakdown = {}
        unique_receivers = set()
        
        all_expenses_list = []
        for exp in general_expenses:
            name = exp.receiver.name if exp.receiver else 'General Expenses'
            if exp.receiver_id: unique_receivers.add(f"gen_{exp.receiver_id}")
            receiver_breakdown[name] = receiver_breakdown.get(name, 0) + float(exp.amount or 0)
            all_expenses_list.append({
                'type': 'General',
                'date': exp.date.strftime('%Y-%m-%d'),
                'receiver': name,
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
            
        for exp in ahmad_expenses:
            name = exp.receiver.name if exp.receiver else 'Ahmad General'
            if exp.receiver_id: unique_receivers.add(f"ahmad_{exp.receiver_id}")
            receiver_breakdown[name] = receiver_breakdown.get(name, 0) + float(exp.amount or 0)
            all_expenses_list.append({
                'type': 'Ahmad',
                'date': exp.date.strftime('%Y-%m-%d'),
                'receiver': name,
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })

        for exp in samer_expenses:
            name = exp.receiver.name if exp.receiver else 'Samer General'
            if exp.receiver_id: unique_receivers.add(f"samer_{exp.receiver_id}")
            receiver_breakdown[name] = receiver_breakdown.get(name, 0) + float(exp.amount or 0)
            all_expenses_list.append({
                'type': 'Samer',
                'date': exp.date.strftime('%Y-%m-%d'),
                'receiver': name,
                'amount': float(exp.amount or 0),
                'note': exp.note or ''
            })
        
        report_data = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_expenses': total_gen + total_ahmad + total_samer,
            'total_receivers': len(unique_receivers),
            'breakdown': {
                'general': total_gen,
                'ahmad': total_ahmad,
                'samer': total_samer
            },
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


if __name__ == '__main__':
    # Debug: Print all registered routes
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)