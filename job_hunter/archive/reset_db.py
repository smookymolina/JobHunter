"""Hard reset: borra tablas en PostgreSQL y limpia outputs/ por completo."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
import shutil
from dotenv import load_dotenv

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUTPUTS_DIR = os.path.join(BASE_DIR, 'outputs')

load_dotenv(os.path.join(BASE_DIR, '.env'))

SCHEMA_SQL = [
    "DROP TABLE IF EXISTS vacantes CASCADE",
    "DROP TABLE IF EXISTS vacantes_eliminadas CASCADE",
    """CREATE TABLE vacantes (
        id                SERIAL PRIMARY KEY,
        user_id           VARCHAR(50) NOT NULL DEFAULT 'default_user',
        titulo            TEXT NOT NULL,
        empresa           TEXT,
        enlace            TEXT UNIQUE,
        requerimientos    TEXT,
        compatibilidad    TEXT CHECK(compatibilidad IN ('Alta','Media','Baja','Nula')) DEFAULT 'Nula',
        status            TEXT CHECK(status IN ('No_Creado','En_Proceso','Revisado_IA','Requiere_Correccion','Listo_Manual')) DEFAULT 'No_Creado',
        fecha_registro    TIMESTAMP DEFAULT NOW(),
        fecha_postulacion TIMESTAMP,
        favorito          INTEGER DEFAULT 0
    )""",
    "CREATE INDEX IF NOT EXISTS idx_vacantes_user ON vacantes(user_id)",
    """CREATE TABLE vacantes_eliminadas (
        id                SERIAL PRIMARY KEY,
        user_id           VARCHAR(50) NOT NULL DEFAULT 'default_user',
        enlace            TEXT NOT NULL,
        titulo            TEXT,
        fecha_eliminacion TIMESTAMP DEFAULT NOW(),
        UNIQUE(user_id, enlace)
    )""",
    # usuarios is NOT dropped on reset — preserve accounts; tier column ensured here
    """CREATE TABLE IF NOT EXISTS usuarios (
        id                       SERIAL PRIMARY KEY,
        user_id                  VARCHAR(50) UNIQUE NOT NULL,
        email                    VARCHAR(255) UNIQUE NOT NULL,
        hashed_password          TEXT NOT NULL,
        tier                     VARCHAR(20) DEFAULT 'free' NOT NULL,
        role                     VARCHAR(20) DEFAULT 'user' NOT NULL,
        telegram_token_encrypted VARCHAR(500) DEFAULT NULL,
        vacantes_limite          INT DEFAULT 5 NOT NULL,
        latex_limite             INT DEFAULT 3 NOT NULL,
        latex_generados          INT DEFAULT 0 NOT NULL,
        created_at               TIMESTAMP DEFAULT NOW()
    )""",
]


def _db():
    _u = _urlparse(os.getenv('DATABASE_URL'))
    return _pg8000.connect(host=_u.hostname, port=_u.port or 5432, user=_u.username, password=_u.password, database=_u.path.lstrip('/'))


def log_diagnostico():
    print("=" * 55)
    print("DIAGNÓSTICO PREVIO AL RESET")
    print("=" * 55)
    try:
        conn = _db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vacantes WHERE user_id='default_user'")
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT status, COUNT(*) FROM vacantes WHERE user_id='default_user' GROUP BY status ORDER BY status"
        )
        by_status = cur.fetchall()
        cur.close()
        conn.close()
        print(f"  Vacantes   : {total}")
        for s, c in by_status:
            print(f"    {s:<25} {c}")
    except Exception as e:
        print(f"  Vacantes   : Error consultando DB: {e}")
    count_files = 0
    if os.path.isdir(OUTPUTS_DIR):
        count_files = sum(1 for f in os.listdir(OUTPUTS_DIR))
    print(f"  Outputs dir: {OUTPUTS_DIR}")
    print(f"  Archivos   : {count_files}")
    print("=" * 55)


def reset():
    print("\n[RESET] Recreando esquema en PostgreSQL...")
    conn = _db()
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in SCHEMA_SQL:
        cur.execute(stmt)
    conn.autocommit = False
    cur.close()
    conn.close()
    print("  Esquema recreado.")

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
    print("[RESET] Hard reset completado.\n")


if __name__ == '__main__':
    log_diagnostico()
    confirm = input("¿Confirmar hard reset? Escribe 'SI' para continuar: ").strip()
    if confirm == 'SI':
        reset()
    else:
        print("[RESET] Cancelado.")
