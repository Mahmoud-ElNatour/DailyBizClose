from app import app
from models import db, AhmadMistrahExpenses, AhmadExpenseReceivers, SamerExpenses, SamerExpenseReceivers
from sqlalchemy import text

def migrate():
    with app.app_context():
        # 1. Create new tables
        try:
            # We use db.create_all() for new tables
            # But the user wants specific names and constraints, so manually executing is safer if we want to be precise like the user asked.
            # Actually, SamerExpenses and receivers are new models in models.py now.
            # So db.create_all() will handle it.
            db.create_all()
            print("New tables created via db.create_all().")
        except Exception as e:
            print(f"Error created tables: {e}")

        # 2. Add receiver_id to ahmad_mistrah_expenses and update types
        try:
            with db.engine.connect() as conn:
                # Check for receiver_id col
                result = conn.execute(text("SHOW COLUMNS FROM ahmad_mistrah_expenses LIKE 'receiver_id'"))
                if not result.fetchone():
                    conn.execute(text("ALTER TABLE ahmad_mistrah_expenses ADD COLUMN receiver_id INT"))
                    conn.execute(text("ALTER TABLE ahmad_mistrah_expenses ADD CONSTRAINT FK_AhmadExpenses_Receiver FOREIGN KEY (receiver_id) REFERENCES ahmad_expense_receivers(id) ON DELETE SET NULL"))
                    conn.execute(text("CREATE INDEX IX_AhmadExpenses_ReceiverId ON ahmad_mistrah_expenses(receiver_id)"))
                    print("Column 'receiver_id' added to 'ahmad_mistrah_expenses'.")
                
                # Update amount type to DECIMAL(18,2)
                conn.execute(text("ALTER TABLE ahmad_mistrah_expenses MODIFY COLUMN amount DECIMAL(18, 2) NOT NULL"))
                print("Updated 'amount' type in 'ahmad_mistrah_expenses'.")
                
                conn.commit()
        except Exception as e:
            print(f"Error updating 'ahmad_mistrah_expenses': {e}")

if __name__ == "__main__":
    migrate()
