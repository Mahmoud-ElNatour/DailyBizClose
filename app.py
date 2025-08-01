import os
import logging
import hashlib

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

# Set up logging for debug mode
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = 'secret_key'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
@login_required
@app.route('/')
def main():
    """Main route - redirects to index"""
    return redirect(url_for('index'))

@login_required
@app.route('/index',methods=['GET'])
def index():
    """Home page route"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            from models import User
            user = User.query.filter_by(username=username).first()
            
            if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
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

@login_required
@app.route('/control-panel')
def control_panel():
    """Control panel page route"""
    return render_template('control_panel.html')

@login_required
@app.route('/daily-close')
def daily_close():
    """Daily close page route"""
    return render_template('daily_close.html')

@login_required
@app.route('/settings')
def settings():
    """Settings page route"""
    return render_template('settings.html')

# API Routes for data management
@app.route('/api/receivers')
def get_receivers():
    """Get all receivers"""
    try:
        from models import Receivers
        receivers = Receivers.query.all()
        return jsonify({
            'receivers': [{
                'id': r.id,
                'name': r.name,
                'paid_by': r.paid_by,
                'note': r.note
            } for r in receivers]
        })
    except Exception as e:
        app.logger.error(f"Error fetching receivers: {e}")
        return jsonify({'error': 'Failed to fetch receivers'}), 500

@app.route('/api/receivers', methods=['POST'])
def create_receiver():
    """Create new receiver"""
    try:
        from models import Receivers
        data = request.get_json()
        
        receiver = Receivers(
            name=data.get('name'),
            paid_by=data.get('paid_by', 'cash'),
            note=data.get('note', '')
        )
        
        db.session.add(receiver)
        db.session.commit()
        
        return jsonify({
            'id': receiver.id,
            'name': receiver.name,
            'paid_by': receiver.paid_by,
            'note': receiver.note
        })
    except Exception as e:
        app.logger.error(f"Error creating receiver: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create receiver'}), 500

@app.route('/api/customers')
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

@app.route('/api/employees')
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

# API Routes for future AJAX integration
@app.route('/api/modules/<module_name>')
def get_module(module_name):
    """API endpoint for module data"""
    # Placeholder for module data - will be expanded later
    return jsonify({
        'module': module_name,
        'status': 'ready',
        'data': f'{module_name.title()} module loaded successfully'
    })

@app.route('/api/daily-closing', methods=['POST'])
def save_daily_closing():
    """API endpoint for saving daily closing data"""
    try:
        from models import DailyClosing, Expenses
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
            expense = Expenses(
                date=close_date,
                amount=expense_data.get('amount', 0),
                daily_closing_id=daily_closing.id,
                receiver_id=expense_data.get('receiver_id')
            )
            db.session.add(expense)
        
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
    app.run(debug=True, host='0.0.0.0', port=5000)