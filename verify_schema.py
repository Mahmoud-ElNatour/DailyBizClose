from app import app
from models import db
from sqlalchemy import text

def verify():
    with app.app_context():
        with db.engine.connect() as conn:
            # Check daily_closing
            res = conn.execute(text("DESCRIBE daily_closing")).fetchall()
            cols = [r[0] for r in res]
            print(f"Columns in daily_closing: {cols}")
            
            # Check deductions_records
            try:
                res2 = conn.execute(text("DESCRIBE deductions_records")).fetchall()
                cols2 = [r[0] for r in res2]
                print(f"Columns in deductions_records: {cols2}")
            except Exception as e:
                print(f"Error describing deductions_records: {e}")

if __name__ == "__main__":
    verify()
