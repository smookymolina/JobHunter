import os
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
from dotenv import load_dotenv

# Load env from parent dir
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUTPUTS_DIR = os.path.join(BASE_DIR, 'outputs')

def _db():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL not found in environment")
    _u = _urlparse(url)
    return _pg8000.connect(host=_u.hostname, port=_u.port or 5432,
                           user=_u.username, password=_u.password,
                           database=_u.path.lstrip('/'))

def get_user_outputs_dir(user_id: str) -> str:
    path = os.path.join(OUTPUTS_DIR, user_id)
    return path

def run():
    conn = _db()
    cur = conn.cursor()
    
    # 1. Get all vacancies with status 'Revisado_IA'
    cur.execute("SELECT id, user_id, titulo FROM vacantes WHERE status='Revisado_IA'")
    rows = cur.fetchall()
    
    if not rows:
        print("No se encontraron vacantes con status 'Revisado_IA'.")
        cur.close()
        conn.close()
        return

    print(f"Se encontraron {len(rows)} vacantes para revertir.")
    
    for vid, user_id, titulo in rows:
        print(f"Procesando vacante #{vid} (user: {user_id}): {titulo}...")
        
        # 2. Reset status to 'No_Creado'
        cur.execute("UPDATE vacantes SET status='No_Creado' WHERE id=%s", (vid,))
        
        # 3. Delete generated files and auxiliary LaTeX files
        out_dir = get_user_outputs_dir(user_id)
        deleted = []
        # Extended extensions to clean everything
        for ext in ("tex", "pdf", "aux", "log", "out", "toc", "nav", "snm"):
            path = os.path.join(out_dir, f"cv_vacante_{vid}.{ext}")
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted.append(ext)
                except OSError as e:
                    print(f"  Error borrando {path}: {e}")
        
        deleted_str = ", ".join(deleted) if deleted else "ninguno"
        print(f"  Status -> No_Creado. Archivos borrados: {deleted_str}")

    # 4. Clear __pycache__ in src
    pycache_dir = os.path.join(BASE_DIR, 'src', '__pycache__')
    if os.path.exists(pycache_dir):
        print(f"\nLimpiando cache de Python: {pycache_dir}")
        import shutil
        try:
            shutil.rmtree(pycache_dir)
            print("  __pycache__ eliminado.")
        except Exception as e:
            print(f"  Error eliminando __pycache__: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nProceso finalizado.")

if __name__ == "__main__":
    run()
