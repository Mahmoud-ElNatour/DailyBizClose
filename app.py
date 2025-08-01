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
        data = request.get_json()
        
        # Log the received data for debugging
        app.logger.debug(f"Received daily close data: {data}")
        
        # Placeholder for database save - will be expanded later
        # Here you would save to the database using SQLAlchemy
        
        return jsonify({
            'status': 'success',
            'message': 'Daily close saved successfully',
            'data': data
        })
    except Exception as e:
        app.logger.error(f"Error saving daily close: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to save daily close'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)