"""
PRODUCTION JOB SYSTEM SPECIFICATION & EXECUTION CONTRACT v1.0
Implementación formal de la máquina de estados y orquestación.
"""

import os
import uuid
import json
import logging
import datetime
from typing import Any, Dict, Optional
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("job_system")

class JobStatus:
    QUEUED = "QUEUED"
    DISPATCHED = "DISPATCHED"
    PROCESSING = "PROCESSING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"
    CANCELLED = "CANCELLED"
    STALE_TIMEOUT = "STALE_TIMEOUT"

class JobType:
    SCRAPE = "SCRAPE"
    LLM_GEN = "LLM_GEN"
    PDF_COMPILE = "PDF_COMPILE"
    MCP_TOOL = "MCP_TOOL"

class JobSystem:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        
    def _db(self):
        _u = _urlparse(self.db_url)
        return _pg8000.connect(
            host=_u.hostname, port=_u.port or 5432,
            user=_u.username, password=_u.password, database=_u.path.lstrip('/')
        )

    def enqueue(self, job_type: str, user_id: str, payload: dict, priority: int = 1, idempotency_key: str = None) -> Optional[str]:
        """Encola un nuevo trabajo. Valida idempotency_key si se provee."""
        conn = self._db()
        cur = conn.cursor()
        job_id = str(uuid.uuid4())
        
        try:
            if idempotency_key:
                cur.execute(
                    "SELECT job_id FROM jobs WHERE idempotency_key=%s AND status IN ('QUEUED', 'PROCESSING', 'COMPLETED')",
                    (idempotency_key,)
                )
                existing = cur.fetchone()
                if existing:
                    log.info("Idempotency match: Job %s ya existe para la clave %s", existing[0], idempotency_key)
                    return existing[0]

            cur.execute(
                """INSERT INTO jobs 
                   (job_id, type, user_id, payload, status, priority, idempotency_key)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (job_id, job_type, user_id, json.dumps(payload), JobStatus.QUEUED, priority, idempotency_key)
            )
            conn.commit()
            log.info("Job %s [%s] encolado exitosamente.", job_id, job_type)
            return job_id
        except Exception as e:
            conn.rollback()
            log.error("Error encolando job: %s", e)
            return None
        finally:
            cur.close()
            conn.close()

    def dispatch(self, job_types: list[str], worker_id: str) -> Optional[dict]:
        """
        Atómico: Encuentra el job más prioritario en QUEUED o RETRYING, 
        lo marca como DISPATCHED y lo devuelve.
        (En un sistema real con Redis se sacaría de la lista, pero la DB es la fuente de la verdad).
        """
        conn = self._db()
        cur = conn.cursor()
        try:
            # SKIP LOCKED es ideal pero pg8000 no soporta sintaxis compleja sin cuidado.
            # Hacemos UPDATE RETURNING si el motor DB lo soporta, o SELECT FOR UPDATE.
            types_str = ",".join(f"'{t}'" for t in job_types)
            query = f"""
                UPDATE jobs 
                SET status = '{JobStatus.DISPATCHED}', dispatched_at = NOW(), error_context = %s
                WHERE job_id = (
                    SELECT job_id FROM jobs 
                    WHERE status IN ('{JobStatus.QUEUED}', '{JobStatus.RETRYING}')
                      AND type IN ({types_str})
                    ORDER BY priority DESC, created_at ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING job_id, type, user_id, payload, retries_current, idempotency_key
            """
            cur.execute(query, (json.dumps({"worker_id": worker_id}),))
            row = cur.fetchone()
            conn.commit()
            if row:
                return {
                    "job_id": row[0],
                    "type": row[1],
                    "user_id": row[2],
                    "payload": json.loads(row[3]) if row[3] else {},
                    "retries_current": row[4],
                    "idempotency_key": row[5]
                }
            return None
        except Exception as e:
            conn.rollback()
            log.error("Error dispatching job: %s", e)
            return None
        finally:
            cur.close()
            conn.close()

    def start_processing(self, job_id: str):
        conn = self._db()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE jobs SET status='{JobStatus.PROCESSING}', started_at=NOW() WHERE job_id=%s AND status='{JobStatus.DISPATCHED}'",
            (job_id,)
        )
        conn.commit()
        cur.close()
        conn.close()

    def mark_completed(self, job_id: str):
        conn = self._db()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE jobs SET status='{JobStatus.COMPLETED}', finished_at=NOW() WHERE job_id=%s",
            (job_id,)
        )
        conn.commit()
        cur.close()
        conn.close()

    def mark_failed(self, job_id: str, error_msg: str, is_retryable: bool):
        conn = self._db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT retries_current, retries_max FROM jobs WHERE job_id=%s", (job_id,))
            row = cur.fetchone()
            if not row: return
            
            curr, mmax = row[0], row[1]
            error_ctx = json.dumps({"error": error_msg, "fatal": not is_retryable})

            if is_retryable and curr < mmax:
                cur.execute(
                    f"UPDATE jobs SET status='{JobStatus.RETRYING}', retries_current=retries_current+1, error_context=%s WHERE job_id=%s",
                    (error_ctx, job_id)
                )
            elif is_retryable and curr >= mmax:
                cur.execute(
                    f"UPDATE jobs SET status='{JobStatus.DEAD_LETTER}', failed_at=NOW(), error_context=%s WHERE job_id=%s",
                    (error_ctx, job_id)
                )
            else:
                cur.execute(
                    f"UPDATE jobs SET status='{JobStatus.FAILED}', failed_at=NOW(), error_context=%s WHERE job_id=%s",
                    (error_ctx, job_id)
                )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def recover_stale_jobs(self, timeout_seconds: int = 600):
        """Marca trabajos colgados en PROCESSING que exceden su lease timeout."""
        conn = self._db()
        cur = conn.cursor()
        cur.execute(
            f"""UPDATE jobs 
               SET status='{JobStatus.STALE_TIMEOUT}' 
               WHERE status='{JobStatus.PROCESSING}' 
                 AND started_at < NOW() - INTERVAL '%s SECONDS'""",
            (timeout_seconds,)
        )
        conn.commit()
        cur.close()
        conn.close()
