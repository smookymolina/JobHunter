import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')))

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


def init_db():
    conn = _db()
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in SCHEMA_SQL:
        cur.execute(stmt)
    cur.close()
    conn.close()
    print("DB PostgreSQL inicializada con esquema multi-tenant.")


if __name__ == '__main__':
    init_db()
