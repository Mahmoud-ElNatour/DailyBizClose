import os
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
    """Employees management page"""
    try:
        from models import Employees
        employees = Employees.query.all()
        return render_template('employees.html', employees=employees)
    except Exception as e:
        app.logger.error(f"Error loading employees: {e}")
        flash('Error loading employees data', 'error')
        return render_template('employees.html', employees=[])

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
        
        return render_template('expenses.html', expenses=expenses, receivers=receivers)
    except Exception as e:
        app.logger.error(f"Error loading expenses: {e}")
        flash('Error loading expenses data', 'error')
        return render_template('expenses.html', expenses=[], receivers=[])

@app.route('/control-panel/sales')
@login_required
def sales():
    """Sales management page"""
    try:
        # Get filter parameters
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        # For now, return placeholder since we don't have a sales table
        # In a real application, you would filter sales by month/year
        return render_template('sales.html')
    except Exception as e:
        app.logger.error(f"Error loading sales: {e}")
        flash('Error loading sales data', 'error')
        return render_template('sales.html')

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
        
        # For now, return all employees since we don't have month/year data in employees table
        # In a real application, you would filter employees by month/year
        employees = Employees.query.all()
        
        return render_template('payroll.html', employees=employees)
    except Exception as e:
        app.logger.error(f"Error loading payroll: {e}")
        flash('Error loading payroll data', 'error')
        return render_template('payroll.html', employees=[])

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
@app.route('/api/receivers')
@login_required
def get_receivers():
    """Get all receivers"""
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

@app.route('/api/receivers', methods=['POST'])
@login_required
def create_receiver():
    """Create new receiver"""
    try:
        from models import Receivers
        data = request.get_json()
        
        receiver = Receivers(
            name=data.get('name'),
            paid_amount=data.get('paid_amount', 0.0)
        )
        
        db.session.add(receiver)
        db.session.commit()
        
        return jsonify({
            'id': receiver.id,
            'name': receiver.name,
            'paid_amount': receiver.paid_amount
        })
    except Exception as e:
        app.logger.error(f"Error creating receiver: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create receiver'}), 500

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
            balance=data.get('balance', 0),
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

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    """Delete customer"""
    try:
        from models import Customers
        customer = Customers.query.get_or_404(customer_id)
        db.session.delete(customer)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Customer deleted successfully'
        })
    except Exception as e:
        app.logger.error(f"Error deleting customer: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete customer'}), 500

@app.route('/api/employees')
@login_required
def get_employees():
    """Get all employees"""
    try:
        from models import Employees
        employees = Employees.query.all()
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
                'total': e.total
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
        data = request.get_json()
        
        employee = Employees(
            name=data.get('name'),
            phone_number=data.get('phone_number'),
            position=data.get('position'),
            base_salary=data.get('base_salary', 0),
            working_days=data.get('working_days', 0),
            actual_working_days=data.get('actual_working_days', 0),
            deductions=data.get('deductions', 0),
            advance=data.get('advance', 0),
            actual_salary=data.get('actual_salary', 0),
            total=data.get('total', 0)
        )
        
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

@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
@login_required
def delete_employee(employee_id):
    """Delete employee"""
    try:
        from models import Employees
        employee = Employees.query.get_or_404(employee_id)
        db.session.delete(employee)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Employee deleted successfully'
        })
    except Exception as e:
        app.logger.error(f"Error deleting employee: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete employee'}), 500

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

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_api(user_id):
    """Delete user via API"""
    try:
        from models import User
        user = User.query.get_or_404(user_id)
        
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
        app.logger.error(f"Error deleting user: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/expenses', methods=['POST'])
@login_required
def create_expense():
    """Create new expense"""
    try:
        from models import Expenses
        from datetime import datetime
        
        data = request.get_json()
        
        expense = Expenses(
            date=datetime.strptime(data.get('date'), '%Y-%m-%d') if data.get('date') else datetime.utcnow(),
            amount=data.get('amount', 0),
            note=data.get('note', ''),
            receiver_id=data.get('receiver_id')
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
        
        # For now, return placeholder data since we don't have a sales table
        # In a real application, you would query the sales table for the specific month/year
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_sales': 0,
            'total_orders': 0,
            'sales': []
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
        # In a real application, you would filter employees by month/year
        # For now, we'll return all employees
        employees = Employees.query.all()
        
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
    """Generate expenses report for month/year"""
    try:
        from datetime import datetime
        from models import Expenses, Receivers
        data = request.get_json()
        month = int(data.get('month'))
        year = int(data.get('year'))
        
        # Get expenses for the specific month/year
        # Filter expenses by month and year
        expenses = Expenses.query.filter(
            db.extract('year', Expenses.date) == year,
            db.extract('month', Expenses.date) == month
        ).all()
        
        total_expenses = sum(exp.amount or 0 for exp in expenses)
        unique_receivers = len(set(exp.receiver_id for exp in expenses if exp.receiver_id))
        
        report_data = {
            'month': data.get('month'),
            'year': data.get('year'),
            'total_expenses': total_expenses,
            'total_receivers': unique_receivers,
            'expenses': [{
                'date': exp.date.strftime('%Y-%m-%d') if exp.date else 'N/A',
                'receiver': exp.receiver.name if exp.receiver else 'N/A',
                'amount': exp.amount or 0,
                'note': exp.note or 'N/A'
            } for exp in expenses]
        }
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
    except Exception as e:
        app.logger.error(f"Error generating expenses report: {e}")
        return jsonify({'error': 'Failed to generate expenses report'}), 500

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

@app.route('/api/daily-closing', methods=['POST'])
@login_required
def save_daily_closing():
    """API endpoint for saving daily closing data"""
    try:
        from models import DailyClosing, Expenses, AhmadMistrahExpenses, Receivers, Customers, Employees
        from datetime import datetime
        
        data = request.get_json()
        
        # Log the received data for debugging
        app.logger.debug(f"Received daily closing data: {data}")
        
        # Parse close date
        close_date = None
        if data.get('date'):
            close_date = datetime.strptime(data.get('date'), '%Y-%m-%d')
        else:
            close_date = datetime.utcnow()

        # Create daily closing record
        daily_closing = DailyClosing(
            date=close_date,
            total_expenses=data.get('total_expenses', 0),
            total_advance=data.get('total_advance', 0),
            total_credit=data.get('total_credit', 0),
            total_cashback=data.get('total_cashback', 0),
            five_percent=data.get('five_percent', 0),
            total_cashout=data.get('total_cashout', 0),
            actual_cash=data.get('actual_cash', 0)
        )
        
        db.session.add(daily_closing)
        db.session.flush()  # Get the ID
        
        # Add individual expenses
        expenses_data = data.get('expenses', [])
        for expense_data in expenses_data:
            # Check if receiver exists, if not create it
            receiver_name = expense_data.get('receiver_name', '')
            receiver = None
            if receiver_name:
                receiver = Receivers.query.filter_by(name=receiver_name).first()
                if not receiver:
                    # Create new receiver
                    receiver = Receivers(
                        name=receiver_name,
                        paid_amount=expense_data.get('amount', 0)
                    )
                    db.session.add(receiver)
                    db.session.flush()  # Get the ID
            
            expense = Expenses(
                date=close_date,
                amount=expense_data.get('amount', 0),
                note=expense_data.get('note', ''),
                daily_closing_id=daily_closing.id,
                receiver_id=receiver.id if receiver else None
            )
            db.session.add(expense)
        
        # Add Ahmad Mistrah expenses
        ahmad_expenses_data = data.get('ahmad_mistrah_expenses', [])
        for ahmad_expense_data in ahmad_expenses_data:
            ahmad_expense = AhmadMistrahExpenses(
                date=close_date,
                amount=ahmad_expense_data.get('amount', 0),
                note=ahmad_expense_data.get('note', ''),
                daily_closing_id=daily_closing.id
            )
            db.session.add(ahmad_expense)
        
        # Handle credits (customers) - subtract from balance
        credits_data = data.get('credits', [])
        for credit_data in credits_data:
            customer_name = credit_data.get('customer_name', '')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    # Create new customer with negative balance (they owe money)
                    customer = Customers(
                        username=customer_name,
                        balance=-credit_data.get('amount', 0),  # Negative balance for credit
                        phone_number=credit_data.get('phone_number', '')
                    )
                    db.session.add(customer)
                    db.session.flush()
                else:
                    # Update existing customer balance (subtract for credit)
                    customer.balance -= credit_data.get('amount', 0)
        
        # Handle cashback (customers) - add to balance
        cashbacks_data = data.get('cashbacks', [])
        for cashback_data in cashbacks_data:
            customer_name = cashback_data.get('customer_name', '')
            if customer_name:
                customer = Customers.query.filter_by(username=customer_name).first()
                if not customer:
                    # Create new customer with positive balance (they get money back)
                    customer = Customers(
                        username=customer_name,
                        balance=cashback_data.get('amount', 0),  # Positive balance for cashback
                        phone_number=cashback_data.get('phone_number', '')
                    )
                    db.session.add(customer)
                    db.session.flush()
                else:
                    # Update existing customer balance (add for cashback)
                    customer.balance += cashback_data.get('amount', 0)
        
        # Handle advances (employees)
        advances_data = data.get('advances', [])
        for advance_data in advances_data:
            employee_name = advance_data.get('employee_name', '')
            if employee_name:
                employee = Employees.query.filter_by(name=employee_name).first()
                if not employee:
                    # Create new employee
                    employee = Employees(
                        name=employee_name,
                        phone_number=advance_data.get('phone_number', ''),
                        position=advance_data.get('position', ''),
                        base_salary=advance_data.get('base_salary', 0),
                        working_days=advance_data.get('working_days', 0),
                        actual_working_days=advance_data.get('actual_working_days', 0),
                        deductions=advance_data.get('deductions', 0),
                        advance=advance_data.get('amount', 0),
                        actual_salary=advance_data.get('actual_salary', 0),
                        total=advance_data.get('total', 0)
                    )
                    db.session.add(employee)
                    db.session.flush()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Daily closing saved successfully',
            'id': daily_closing.id
        })
        
    except Exception as e:
        app.logger.error(f"Error saving daily closing: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to save daily closing'
        }), 500

if __name__ == '__main__':
    # Debug: Print all registered routes
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)