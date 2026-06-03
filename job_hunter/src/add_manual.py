import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'vacantes.db')

def add_manual(titulo, empresa, enlace, requerimientos, compatibilidad="Nula"):
    if not os.path.exists(DB_PATH):
        print("ERROR: DB no encontrada. Ejecuta primero init_db.py")
        return None

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO vacantes
               (titulo, empresa, enlace, requerimientos, compatibilidad, status)
               VALUES (?,?,?,?,?,'No_Creado')""",
            (titulo[:200], empresa[:100], enlace, requerimientos[:2000], compatibilidad)
        )
        conn.commit()
        row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        changes = conn.execute("SELECT changes()").fetchone()[0]
        conn.close()
        if changes:
            print(f"✓ Vacante insertada con ID={row_id}: {titulo[:60]}")
            return row_id
        else:
            print(f"! Vacante duplicada (enlace ya existe): {enlace[:80]}")
            return None
    except Exception as e:
        print(f"ERROR: {e}")
        conn.close()
        return None

def interactive():
    print("=== Agregar Vacante Manual ===\n")
    titulo        = input("Título del puesto : ").strip()
    empresa       = input("Empresa           : ").strip() or "Desconocida"
    enlace        = input("Enlace (URL)      : ").strip()
    print("Requerimientos (escribe, Enter x2 para terminar):")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    requerimientos = "\n".join(lines)

    print("\nCompatibilidad [Alta / Media / Baja / Nula] (Enter = Nula):")
    compat = input().strip().capitalize() or "Nula"
    if compat not in ("Alta", "Media", "Baja", "Nula"):
        compat = "Nula"

    add_manual(titulo, empresa, enlace, requerimientos, compat)

if __name__ == '__main__':
    interactive()
