import sys
import os

# Ensure we can import from the app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db
from models import EmployeeWorking

def recalculate_all():
    with app.app_context():
        records = EmployeeWorking.query.all()
        count = 0
        for record in records:
            old_salary = record.actual_salary
            record.calculate_salary()
            if old_salary != record.actual_salary:
                count += 1
                print(f"Updated record {record.id} for Employee {record.employee_id} ({record.year}-{record.month}): {old_salary} -> {record.actual_salary}")
        
        db.session.commit()
        print(f"Successfully recalculated salaries. {count} records updated.")

if __name__ == '__main__':
    recalculate_all()
