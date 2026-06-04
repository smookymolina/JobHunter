import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db', 'vacantes.db'))

SCHEMA_SQL = """
DROP TABLE IF EXISTS vacantes;
DROP TABLE IF EXISTS vacantes_eliminadas;
CREATE TABLE vacantes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo            TEXT NOT NULL,
    empresa           TEXT,
    enlace            TEXT UNIQUE,
    requerimientos    TEXT,
    compatibilidad    TEXT CHECK(compatibilidad IN ('Alta','Media','Baja','Nula')) DEFAULT 'Nula',
    status            TEXT CHECK(status IN ('No_Creado','En_Proceso','Revisado_IA','Requiere_Correccion','Listo_Manual')) DEFAULT 'No_Creado',
    fecha_registro    TEXT DEFAULT (datetime('now', 'localtime')),
    fecha_postulacion TEXT
);
CREATE TABLE vacantes_eliminadas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    enlace            TEXT UNIQUE NOT NULL,
    titulo            TEXT,
    fecha_eliminacion TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"DB inicializada en: {os.path.abspath(DB_PATH)}")

if __name__ == '__main__':
    init_db()
