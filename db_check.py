from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        with db.engine.connect() as conn:
            print("--- TABLES ---")
            tables = conn.execute(text('SHOW TABLES')).fetchall()
            for t in tables:
                print(t[0])
            
            print("\n--- EMPLOYEES SCHEMA ---")
            columns = conn.execute(text('DESCRIBE employees')).fetchall()
            for c in columns:
                print(c)
                
            print("\n--- EMPLOYEEWORKING SCHEMA ---")
            try:
                columns_w = conn.execute(text('DESCRIBE employeeworking')).fetchall()
                for c in columns_w:
                    print(c)
            except Exception as e:
                print(f"Error describing employeeworking: {e}")
    except Exception as e:
        print(f"Database error: {e}")
