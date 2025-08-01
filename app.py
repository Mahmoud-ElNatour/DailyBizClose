import os
import logging

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging for debug mode
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    try:
        import models  # noqa: F401
    except ImportError:
        pass  # Models file doesn't exist yet
    db.create_all()

# Routes
@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html')

@app.route('/control-panel')
def control_panel():
    """Control panel page route"""
    return render_template('control_panel.html')

@app.route('/daily-close')
def daily_close():
    """Daily close page route"""
    return render_template('daily_close.html')

# API Routes for categories
@app.route('/api/categories/<category_type>')
def get_categories(category_type):
    """Get categories for dropdown lists"""
    try:
        from models import (ExpenseCategory, AdvanceCategory, CreditCategory, 
                          CashbackCategory, ExpenseCategorySamer)
        
        category_models = {
            'expense': ExpenseCategory,
            'advance': AdvanceCategory,
            'credit': CreditCategory,
            'cashback': CashbackCategory,
            'samer-expense': ExpenseCategorySamer
        }
        
        if category_type not in category_models:
            return jsonify({'error': 'Invalid category type'}), 400
        
        model = category_models[category_type]
        categories = model.query.all()
        
        return jsonify({
            'categories': [{'id': cat.id, 'name': cat.name} for cat in categories]
        })
    except Exception as e:
        app.logger.error(f"Error fetching categories: {e}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

@app.route('/api/categories/<category_type>', methods=['POST'])
def create_category(category_type):
    """Create new category if it doesn't exist"""
    try:
        from models import (ExpenseCategory, AdvanceCategory, CreditCategory, 
                          CashbackCategory, ExpenseCategorySamer)
        
        data = request.get_json()
        category_name = data.get('name', '').strip()
        
        if not category_name:
            return jsonify({'error': 'Category name is required'}), 400
        
        category_models = {
            'expense': ExpenseCategory,
            'advance': AdvanceCategory,
            'credit': CreditCategory,
            'cashback': CashbackCategory,
            'samer-expense': ExpenseCategorySamer
        }
        
        if category_type not in category_models:
            return jsonify({'error': 'Invalid category type'}), 400
        
        model = category_models[category_type]
        
        # Check if category already exists
        existing = model.query.filter_by(name=category_name).first()
        if existing:
            return jsonify({
                'id': existing.id,
                'name': existing.name,
                'exists': True
            })
        
        # Create new category
        new_category = model(name=category_name)
        db.session.add(new_category)
        db.session.commit()
        
        return jsonify({
            'id': new_category.id,
            'name': new_category.name,
            'exists': False
        })
        
    except Exception as e:
        app.logger.error(f"Error creating category: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create category'}), 500

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

@app.route('/api/daily-close', methods=['POST'])
def save_daily_close():
    """API endpoint for saving daily close data"""
    try:
        from models import (DailyClose, ExpenseTransaction, AdvanceTransaction, 
                          CreditTransaction, CashbackTransaction, SamerExpenseTransaction)
        
        data = request.get_json()
        
        # Log the received data for debugging
        app.logger.debug(f"Received daily close data: {data}")
        
        # Parse close date
        from datetime import datetime
        close_date = None
        if data.get('close_date'):
            close_date = datetime.strptime(data.get('close_date'), '%Y-%m-%d').date()
        else:
            close_date = datetime.utcnow().date()

        # Create daily close record
        daily_close = DailyClose(
            close_date=close_date,
            main_reading=data.get('main_reading', 0),
            dr_smashed=data.get('dr_smashed', 0),
            ahmad_expenses=data.get('ahmad_expenses', 0),
            adjusted_reading=data.get('adjusted_reading', 0),
            five_percent=data.get('five_percent', 0),
            actual_cash=data.get('actual_cash', 0)
        )
        
        db.session.add(daily_close)
        db.session.flush()  # Get the ID
        
        # Add transactions
        transaction_models = {
            'expenses': (ExpenseTransaction, 'expense_category_id'),
            'advances': (AdvanceTransaction, 'advance_category_id'),
            'credits': (CreditTransaction, 'credit_category_id'),
            'cashbacks': (CashbackTransaction, 'cashback_category_id'),
            'samer_expenses': (SamerExpenseTransaction, 'samer_expense_category_id')
        }
        
        for transaction_type, (model, category_field) in transaction_models.items():
            transactions = data.get(transaction_type, [])
            for trans in transactions:
                transaction = model(
                    daily_close_id=daily_close.id,
                    category_id=trans.get('category_id'),
                    amount=trans.get('amount', 0),
                    description=trans.get('description', '')
                )
                db.session.add(transaction)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Daily close saved successfully',
            'id': daily_close.id
        })
        
    except Exception as e:
        app.logger.error(f"Error saving daily close: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Failed to save daily close'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)