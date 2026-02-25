
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mah!moud123",
        database="dailybizclose"
    )
    cursor = conn.cursor()
    
    print("Employees data (first 5 rows):")
    cursor.execute("SELECT id, name, year, month FROM employees LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\nEmployee_working data (first 5 rows):")
    cursor.execute("SELECT id, employee_id, year, month FROM employee_working LIMIT 5")
    for row in cursor.fetchall():
        print(row)
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
