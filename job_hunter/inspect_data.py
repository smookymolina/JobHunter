import sqlite3
import os

DB_PATH = r"C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\db\vacantes.db"

def inspect_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- 5 samples ---")
    cursor.execute("SELECT id, titulo, empresa, status FROM vacantes LIMIT 5")
    for row in cursor.fetchall():
        print(row)
        
    print("\n--- 'Desconocida' check ---")
    cursor.execute("SELECT COUNT(*) FROM vacantes WHERE empresa = 'Desconocida'")
    count = cursor.fetchone()[0]
    print(f"Total 'Desconocida': {count}")
    
    conn.close()

if __name__ == "__main__":
    inspect_data()
