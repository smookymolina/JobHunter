import sqlite3
import os

DB_PATH = r"C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\db\vacantes.db"

def clean_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vacantes WHERE empresa = 'Desconocida'")
    conn.commit()
    print(f"Deleted {cursor.rowcount} rows with 'Desconocida' company.")
    conn.close()

if __name__ == "__main__":
    clean_db()
