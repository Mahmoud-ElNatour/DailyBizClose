from app import app
from models import db
from sqlalchemy import text

def update_schema():
    with app.app_context():
        with db.engine.connect() as conn:
            print("Adding sales columns to daily_closing table...")
            try:
                conn.execute(text("ALTER TABLE daily_closing ADD COLUMN main_reading FLOAT NOT NULL DEFAULT 0.0"))
                print("Added main_reading")
            except Exception as e:
                print(f"main_reading column might already exist: {e}")

            try:
                conn.execute(text("ALTER TABLE daily_closing ADD COLUMN dr_smashed FLOAT NOT NULL DEFAULT 0.0"))
                print("Added dr_smashed")
            except Exception as e:
                print(f"dr_smashed column might already exist: {e}")

            try:
                conn.execute(text("ALTER TABLE daily_closing ADD COLUMN adjusted_reading FLOAT NOT NULL DEFAULT 0.0"))
                print("Added adjusted_reading")
            except Exception as e:
                print(f"adjusted_reading column might already exist: {e}")
            
            conn.commit()
            print("Successfully updated daily_closing schema.")

if __name__ == "__main__":
    update_schema()
