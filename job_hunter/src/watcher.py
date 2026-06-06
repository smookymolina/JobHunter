import os
import pg8000.dbapi as _pg8000
from urllib.parse import urlparse as _urlparse
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')))

from gemini_engine import OUTPUTS_DIR, compilar_pdf

SYNC_STATUSES = {"No_Creado", "En_Proceso", "Revisado_IA", "Requiere_Correccion", "Listo_Manual"}
_VACANTE_COLS = ["id", "titulo", "empresa", "enlace", "requerimientos", "compatibilidad", "status", "fecha_registro"]


def _db():
    _u = _urlparse(os.getenv('DATABASE_URL'))
    return _pg8000.connect(host=_u.hostname, port=_u.port or 5432, user=_u.username, password=_u.password, database=_u.path.lstrip('/'))


def _set_status(vacante_id: int, status: str) -> None:
    conn = _db()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE vacantes SET status=%s WHERE id=%s AND user_id='default_user'",
            (status, vacante_id)
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _pdf_path(vacante_id: int) -> str:
    return os.path.abspath(os.path.join(OUTPUTS_DIR, f"cv_vacante_{vacante_id}.pdf"))


def _tex_path(vacante_id: int) -> str:
    return os.path.abspath(os.path.join(OUTPUTS_DIR, f"cv_vacante_{vacante_id}.tex"))


def _fetch_vacantes(limit: int | None = None) -> list[dict[str, Any]]:
    conn = _db()
    try:
        cur = conn.cursor()
        query = (
            "SELECT id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro "
            "FROM vacantes WHERE user_id='default_user' ORDER BY id DESC"
        )
        params: tuple[Any, ...] = ()
        if limit:
            query += " LIMIT %s"
            params = (limit,)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(zip(_VACANTE_COLS, row)) for row in rows]
    finally:
        conn.close()


def _vacante_sync_state(vacante: dict[str, Any]) -> dict[str, Any]:
    vid = int(vacante["id"])
    pdf = _pdf_path(vid)
    tex = _tex_path(vid)
    return {
        "id": vid,
        "status": vacante.get("status", "No_Creado"),
        "pdf_exists": os.path.exists(pdf),
        "tex_exists": os.path.exists(tex),
        "pdf": pdf,
        "tex": tex,
    }


def _sync_one(vacante: dict[str, Any], dry_run: bool = True) -> dict[str, Any]:
    state = _vacante_sync_state(vacante)
    desired = None
    error = None

    if state["status"] == "Listo_Manual":
        return {**state, "desired_status": None, "changed": False, "error": None}

    if state["pdf_exists"]:
        desired = "Revisado_IA"
    elif state["tex_exists"]:
        try:
            if not dry_run:
                compilar_pdf(state["tex"])
            else:
                desired = "Revisado_IA"
            desired = "Revisado_IA"
        except Exception as exc:
            desired = "Requiere_Correccion"
            error = str(exc)

    changed = desired is not None and desired != state["status"] and not dry_run
    if changed and desired:
        _set_status(state["id"], desired)

    return {
        **state,
        "desired_status": desired,
        "changed": changed,
        "error": error,
    }


def deep_health_check(limit: int = 50, dry_run: bool = True) -> dict[str, Any]:
    vacantes = _fetch_vacantes(limit)
    by_status: dict[str, int] = {k: 0 for k in SYNC_STATUSES}
    issues: list[dict[str, Any]] = []
    ok = True

    for vacante in vacantes:
        status = vacante.get("status", "No_Creado")
        if status in by_status:
            by_status[status] += 1
        else:
            by_status[status] = by_status.get(status, 0) + 1

        sync_state = _sync_one(vacante, dry_run=dry_run)
        if sync_state["desired_status"] and sync_state["desired_status"] != sync_state["status"]:
            issues.append(sync_state)
            ok = False

    total = len(vacantes)
    healthy = ok and total >= 0
    state = "healthy" if healthy else "degraded"
    if total == 0:
        state = "idle"

    return {
        "ok": healthy,
        "state": state,
        "total": total,
        "by_status": by_status,
        "issues": issues[:15],
        "dry_run": dry_run,
        "timestamp": time.time(),
    }


@dataclass
class DeepHealthWatcher:
    interval_seconds: int = 30
    dry_run: bool = False
    _stop: threading.Event = field(default_factory=threading.Event, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)
    _last_snapshot: dict[str, Any] = field(default_factory=dict, init=False)
    _last_error: str | None = field(default=None, init=False)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="deep-health-watcher")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "last_error": self._last_error,
            "last_snapshot": self._last_snapshot,
        }

    def check_now(self, dry_run: bool | None = None) -> dict[str, Any]:
        snapshot = deep_health_check(dry_run=self.dry_run if dry_run is None else dry_run)
        self._last_snapshot = snapshot
        self._last_error = None
        return snapshot

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._last_snapshot = deep_health_check(dry_run=self.dry_run)
                self._last_error = None
            except Exception as exc:
                self._last_error = str(exc)
            self._stop.wait(self.interval_seconds)
