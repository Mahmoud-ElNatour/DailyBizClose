from app import app
from models import DailyClosing

def verify_fields():
    with app.app_context():
        try:
            # Check if fields exist in model
            c = DailyClosing()
            fields = ['main_reading', 'dr_smashed', 'adjusted_reading']
            for f in fields:
                if hasattr(c, f):
                    print(f"Field {f} exists in model")
                else:
                    print(f"CRITICAL: Field {f} MISSING from model")
            
            # Check if they can be queried
            closing = DailyClosing.query.first()
            if closing:
                print(f"Sample data - Adjusted Reading: {closing.adjusted_reading}")
            else:
                print("No daily closings found in database yet.")

        except Exception as e:
            print(f"Error during verification: {e}")

if __name__ == "__main__":
    verify_fields()
