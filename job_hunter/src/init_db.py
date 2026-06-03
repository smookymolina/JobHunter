import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'vacantes.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS vacantes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT NOT NULL,
            empresa         TEXT,
            enlace          TEXT UNIQUE,
            requerimientos  TEXT,
            compatibilidad  TEXT CHECK(compatibilidad IN ('Alta','Media','Baja','Nula')) DEFAULT 'Nula',
            status          TEXT CHECK(status IN ('No_Creado','En_Proceso','Revisado_IA','Listo_Manual')) DEFAULT 'No_Creado',
            fecha_registro  TEXT DEFAULT (datetime('now'))
        )
    ''')
    conn.commit()
    conn.close()
    print(f"DB inicializada en: {os.path.abspath(DB_PATH)}")

if __name__ == '__main__':
    init_db()
