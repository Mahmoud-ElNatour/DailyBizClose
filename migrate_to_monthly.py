
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mah!moud123",
        database="dailybizclose"
    )
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get all data from employees
    cursor.execute("SELECT * FROM employees")
    old_employees = cursor.fetchall()
    
    # 2. Identify unique employees by name
    unique_employees = {}
    for row in old_employees:
        name = row['name']
        if name not in unique_employees:
            unique_employees[name] = {
                'phone_number': row['phone_number'],
                'position': row['position'],
                'base_salary': row['base_salary'],
                'ids': [] # ids in the original table
            }
        unique_employees[name]['ids'].append(row['id'])

    print(f"Found {len(unique_employees)} unique employees.")

    # 3. Create or Update unique employees
    # For each unique employee, we'll keep the first ID we found as the master ID if possible, 
    # but since we want to cleanup the table, maybe it's better to create a temporary mapping.
    
    # Actually, we can just insert unique employees into a temporary table or just handle it carefully.
    # Let's try to do it in-place if possible, but safer to create new entries and then cleanup.
    
    # Better approach:
    # A. Create a list of (master_id, name)
    # B. For each unique name, designate one ID as master.
    # C. For all other IDs of the same name, update references in advances and deductions_records to point to master_id.
    # D. Insert monthly data into employee_working pointing to master_id.
    # E. Delete non-master rows from employees.
    # F. Remove monthly columns from employees.
    
    for name, info in unique_employees.items():
        master_id = info['ids'][0]
        print(f"Processing {name} (Master ID: {master_id}, Alternatives: {info['ids'][1:]})")
        
        # Update references for other IDs
        for other_id in info['ids'][1:]:
            print(f"  Merging ID {other_id} into {master_id}")
            cursor.execute("UPDATE advances SET employee_id = %s WHERE employee_id = %s", (master_id, other_id))
            cursor.execute("UPDATE deductions_records SET employee_id = %s WHERE employee_id = %s", (master_id, other_id))
            
        # Move monthly data to employee_working
        from datetime import datetime
        now = datetime.now()
        
        for old_id in info['ids']:
            cursor.execute("SELECT * FROM employees WHERE id = %s", (old_id,))
            row = cursor.fetchone()
            
            year = row['year'] if row['year'] is not None else now.year
            month = row['month'] if row['month'] is not None else now.month
            
            def safe_f(val):
                return float(val) if val is not None else 0.0

            # Use columns found in physical schema
            cursor.execute("""
                INSERT IGNORE INTO employee_working 
                (employee_id, year, month, working_days, actual_working_days, deductions_total, advance_total, actual_salary, total)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                master_id, 
                year, 
                month, 
                safe_f(row['working_days']), 
                safe_f(row['actual_working_days']), 
                safe_f(row['deductions']), 
                safe_f(row['advance']), 
                safe_f(row['actual_salary']), 
                safe_f(row['total'])
            ))
            
        # Delete non-master rows
        for other_id in info['ids'][1:]:
            cursor.execute("DELETE FROM employees WHERE id = %s", (other_id,))

    conn.commit()
    print("Migration completed successfully.")
    conn.close()
except Exception as e:
    print(f"Error during migration: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
