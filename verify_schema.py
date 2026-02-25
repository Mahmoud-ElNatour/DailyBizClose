from app import app
from models import db
from sqlalchemy import text

def verify():
    with app.app_context():
        with db.engine.connect() as conn:

            # Get current database name
            db_name = conn.execute(text("SELECT DATABASE()")).scalar()

            # Get all tables
            tables = conn.execute(text("""
                SELECT TABLE_NAME
                FROM information_schema.tables
                WHERE table_schema = :db
                ORDER BY TABLE_NAME
            """), {"db": db_name}).fetchall()

            for table in tables:
                table_name = table[0]

                # Get columns for each table
                cols = conn.execute(text("""
                    SELECT COLUMN_NAME
                    FROM information_schema.columns
                    WHERE table_schema = :db
                    AND table_name = :table
                    ORDER BY ORDINAL_POSITION
                """), {"db": db_name, "table": table_name}).fetchall()

                col_list = [c[0] for c in cols]
                print(f"\n📦 Table: {table_name}")
                print(f"   Columns: {col_list}")

if __name__ == "__main__":
    verify()