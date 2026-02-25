
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Mah!moud123",
        database="dailybizclose"
    )
    cursor = conn.cursor()
    
    for table_name in ['advances', 'deductions_records']:
        print(f"\nSchema for {table_name}:")
        try:
            cursor.execute(f"DESCRIBE {table_name}")
            for row in cursor.fetchall():
                print(row)
        except Exception as e:
            print(f"Table {table_name} error/not found: {e}")
            
    conn.close()
except Exception as e:
    print(f"Connection error: {e}")
