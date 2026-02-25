
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mah!moud123",
        database="dailybizclose"
    )
    cursor = conn.cursor()
    
    print("Checking for duplicate names in employees:")
    cursor.execute("SELECT name, COUNT(*) FROM employees GROUP BY name HAVING COUNT(*) > 1")
    for row in cursor.fetchall():
        print(row)
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
