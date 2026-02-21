from app import app
from models import db, DailyClosing, Deductions
from sqlalchemy import text

def migrate():
    with app.app_context():
        # 1. Create the deductions_records table if it doesn't exist
        # db.create_all() will create missing tables but not update existing ones
        try:
            Deductions.__table__.create(db.engine)
            print("Table 'deductions_records' created.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Table 'deductions_records' already exists.")
            else:
                print(f"Error creating table 'deductions_records': {e}")

        # 2. Add total_deductions column to daily_closing table
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE daily_closing ADD COLUMN total_deductions FLOAT NOT NULL DEFAULT 0.0"))
                conn.commit()
                print("Column 'total_deductions' added to 'daily_closing' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'total_deductions' already exists in 'daily_closing' table.")
            else:
                print(f"Error adding column 'total_deductions': {e}")

if __name__ == "__main__":
    migrate()
