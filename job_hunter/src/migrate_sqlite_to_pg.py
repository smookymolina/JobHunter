"""ETL: Migra vacantes y blacklist de SQLite → PostgreSQL con user_id='default_user'."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import sqlite3
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
from dotenv import load_dotenv

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SQLITE_PATH = os.path.join(BASE_DIR, 'db', 'vacantes.db')

load_dotenv(os.path.join(BASE_DIR, '.env'))


def migrate():
    if not os.path.exists(SQLITE_PATH):
        print(f"SQLite DB no encontrada en {SQLITE_PATH}. Nada que migrar.")
        return

    src = sqlite3.connect(SQLITE_PATH)
    _u = _urlparse(os.getenv('DATABASE_URL'))
    dst = _pg8000.connect(host=_u.hostname, port=_u.port or 5432, user=_u.username, password=_u.password, database=_u.path.lstrip('/'))
    dst_cur = dst.cursor()

    src_cur = src.execute("SELECT * FROM vacantes")
    cols = [d[0] for d in src_cur.description]
    rows = src_cur.fetchall()
    print(f"Migrando {len(rows)} vacantes...")
    migradas = 0
    for row in rows:
        d = dict(zip(cols, row))
        dst_cur.execute(
            "INSERT INTO vacantes "
            "(user_id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro, fecha_postulacion, favorito) "
            "VALUES ('default_user',%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (enlace) DO NOTHING",
            (
                d.get('titulo'),
                d.get('empresa'),
                d.get('enlace'),
                d.get('requerimientos'),
                d.get('compatibilidad', 'Nula'),
                d.get('status', 'No_Creado'),
                d.get('fecha_registro'),
                d.get('fecha_postulacion'),
                d.get('favorito', 0),
            )
        )
        migradas += dst_cur.rowcount

    try:
        src_cur2 = src.execute("SELECT * FROM vacantes_eliminadas")
        cols2 = [d[0] for d in src_cur2.description]
        rows2 = src_cur2.fetchall()
        print(f"Migrando {len(rows2)} entradas en blacklist...")
        bl_migradas = 0
        for row in rows2:
            d = dict(zip(cols2, row))
            dst_cur.execute(
                "INSERT INTO vacantes_eliminadas (user_id, enlace, titulo, fecha_eliminacion) "
                "VALUES ('default_user',%s,%s,%s) ON CONFLICT (user_id, enlace) DO NOTHING",
                (
                    d.get('enlace'),
                    d.get('titulo'),
                    d.get('fecha_eliminacion'),
                )
            )
            bl_migradas += dst_cur.rowcount
        print(f"  Blacklist migrada: {bl_migradas} entradas.")
    except Exception as e:
        print(f"  Blacklist omitida: {e}")

    dst.commit()
    dst_cur.close()
    src.close()
    dst.close()
    print(f"Migracion completada: {migradas} vacantes migradas a PostgreSQL.")


if __name__ == '__main__':
    migrate()
