import sqlite3
import os

DB_PATH = r"C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\db\vacantes.db"

def check_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(vacantes)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
