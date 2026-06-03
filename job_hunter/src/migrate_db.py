"""
Migración: añade 'Requiere_Correccion' a los CHECK válidos de status.
SQLite no soporta ALTER TABLE ... MODIFY, así que se recrea la tabla.
Ejecutar una sola vez: python src/migrate_db.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'vacantes.db')

NEW_CHECK = "('No_Creado','En_Proceso','Revisado_IA','Listo_Manual','Requiere_Correccion')"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Verificar si la migración ya se aplicó
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vacantes'")
    ddl = c.fetchone()
    if ddl and 'Requiere_Correccion' in ddl[0]:
        print("Migración ya aplicada. Nada que hacer.")
        conn.close()
        return

    print("Aplicando migración...")
    c.executescript(f"""
        PRAGMA foreign_keys=OFF;
        BEGIN TRANSACTION;

        CREATE TABLE vacantes_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT NOT NULL,
            empresa         TEXT,
            enlace          TEXT UNIQUE,
            requerimientos  TEXT,
            compatibilidad  TEXT CHECK(compatibilidad IN ('Alta','Media','Baja','Nula')) DEFAULT 'Nula',
            status          TEXT CHECK(status IN {NEW_CHECK}) DEFAULT 'No_Creado',
            fecha_registro  TEXT DEFAULT (datetime('now'))
        );

        INSERT INTO vacantes_new SELECT * FROM vacantes;
        DROP TABLE vacantes;
        ALTER TABLE vacantes_new RENAME TO vacantes;

        COMMIT;
        PRAGMA foreign_keys=ON;
    """)
    conn.close()
    print(f"✓ Migración completada. Status 'Requiere_Correccion' habilitado.")

if __name__ == '__main__':
    migrate()
