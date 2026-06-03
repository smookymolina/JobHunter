"""Hard reset: borra la DB completa y limpia outputs/ por completo."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import sqlite3
import shutil

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DB_PATH     = os.path.join(BASE_DIR, 'db', 'vacantes.db')
OUTPUTS_DIR = os.path.join(BASE_DIR, 'outputs')
SCHEMA_SQL   = """
CREATE TABLE vacantes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo          TEXT NOT NULL,
    empresa         TEXT,
    enlace          TEXT UNIQUE,
    requerimientos  TEXT,
    compatibilidad  TEXT CHECK(compatibilidad IN ('Alta','Media','Baja','Nula')) DEFAULT 'Nula',
    status          TEXT CHECK(status IN ('No_Creado','En_Proceso','Revisado_IA','Requiere_Correccion','Listo_Manual')) DEFAULT 'No_Creado',
    fecha_registro  TEXT DEFAULT (datetime('now'))
);
"""

# ── Diagnóstico previo ────────────────────────────────────────────────────────

def log_diagnostico():
    print("=" * 55)
    print("DIAGNÓSTICO PREVIO AL RESET")
    print("=" * 55)
    print(f"  DB         : {DB_PATH}")
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) FROM vacantes GROUP BY status ORDER BY status"
        ).fetchall()
        conn.close()
        print(f"  Vacantes   : {total}")
        for s, c in by_status:
            print(f"    {s:<25} {c}")
    else:
        print("  Vacantes   : DB ausente")
    count_files = 0
    if os.path.isdir(OUTPUTS_DIR):
        count_files = sum(1 for f in os.listdir(OUTPUTS_DIR))
    print(f"  Outputs dir: {OUTPUTS_DIR}")
    print(f"  Archivos   : {count_files}")
    print("=" * 55)


def reset():
    print("\n[RESET] Eliminando base de datos...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("  DB eliminada")
    else:
        print("  DB no existía")

    print("[RESET] Limpiando outputs/...")
    removed = 0
    if os.path.isdir(OUTPUTS_DIR):
        for f in os.listdir(OUTPUTS_DIR):
            path = os.path.join(OUTPUTS_DIR, f)
            if os.path.isdir(path):
                shutil.rmtree(path)
                removed += 1
            else:
                os.remove(path)
                removed += 1
    print(f"  Archivos eliminados: {removed}")

    print("[RESET] Recreando esquema...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print("  Esquema recreado con defaults correctos")
    print("[RESET] Hard reset completado.\n")


if __name__ == '__main__':
    log_diagnostico()
    confirm = input("¿Confirmar hard reset? Escribe 'SI' para continuar: ").strip()
    if confirm == 'SI':
        reset()
    else:
        print("[RESET] Cancelado.")
