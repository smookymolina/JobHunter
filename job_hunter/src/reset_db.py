"""Hard reset: borra todas las vacantes de la DB y archivos .tex/.pdf de outputs/."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import sqlite3

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH     = os.path.join(BASE_DIR, 'db', 'vacantes.db')
OUTPUTS_DIR = os.path.join(BASE_DIR, 'outputs')

# ── Diagnóstico previo ────────────────────────────────────────────────────────

def log_diagnostico():
    print("=" * 55)
    print("DIAGNÓSTICO PREVIO AL RESET")
    print("=" * 55)
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0]
    by_status = conn.execute(
        "SELECT status, COUNT(*) FROM vacantes GROUP BY status ORDER BY status"
    ).fetchall()
    conn.close()
    print(f"  DB         : {DB_PATH}")
    print(f"  Vacantes   : {total}")
    for s, c in by_status:
        print(f"    {s:<25} {c}")
    count_files = 0
    if os.path.isdir(OUTPUTS_DIR):
        count_files = sum(1 for f in os.listdir(OUTPUTS_DIR) if f.endswith(('.tex', '.pdf')))
    print(f"  Outputs dir: {OUTPUTS_DIR}")
    print(f"  Archivos   : {count_files} (.tex + .pdf)")
    print("=" * 55)


def reset():
    print("\n[RESET] Limpiando base de datos...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM vacantes")
    try:
        conn.execute("DELETE FROM sqlite_sequence WHERE name='vacantes'")
    except Exception:
        pass
    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0]
    conn.close()
    print(f"  Vacantes restantes: {remaining}")

    print("[RESET] Limpiando outputs/...")
    removed = 0
    if os.path.isdir(OUTPUTS_DIR):
        for f in os.listdir(OUTPUTS_DIR):
            if f.endswith(('.tex', '.pdf')):
                os.remove(os.path.join(OUTPUTS_DIR, f))
                removed += 1
    print(f"  Archivos eliminados: {removed}")
    print("[RESET] Hard reset completado.\n")


if __name__ == '__main__':
    log_diagnostico()
    confirm = input("¿Confirmar hard reset? Escribe 'SI' para continuar: ").strip()
    if confirm == 'SI':
        reset()
    else:
        print("[RESET] Cancelado.")
