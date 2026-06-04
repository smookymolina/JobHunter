# Job Hunter

Sistema local para automatizar la busqueda de empleo, generar CVs en LaTeX y coordinar el flujo IA sobre SQLite.

## Lectura base
- `docs/README_IA.md`
- `docs/ARQUITECTURA_Y_BD.md`
- `docs/PIPELINE_IA.md`

## Resumen operativo
- Backend FastAPI en `job_hunter/src/api.py`
- MCP server en `job_hunter/src/mcp_server.py`
- Frontend Next.js en `frontend/`
- Base de datos SQLite en `job_hunter/db/vacantes.db`
- PDF local con `pdflatex`

## Flujo
```text
vacante -> SQLite -> API -> MCP/IA -> .tex -> pdflatex -> PDF -> Revisado_IA
```

## Cambios clave
- `browser_agent.py` usa `POST /vacantes` (nunca SQLite directo) — elimina bloqueos WAL.
- Nuevo endpoint `POST /generar_cv/{id}`: bot genera CVs 100% vía API, sin imports locales.
- Dashboard polling a **2 s** + `Cache-Control: no-store` en `/vacantes`.
- Bot Telegram: todas las acciones muestran botón ◀️ Menú Principal al finalizar.
- **Blacklist**: vacante eliminada → enlace en `vacantes_eliminadas` → nunca reaparece en scrapes.
- **CV Enviado**: marcar `Listo_Manual` registra `fecha_postulacion`; tarjeta muestra "CV enviado — esperando respuesta".
- **Watcher fix**: `_sync_one` ya no revierte `Listo_Manual` a `Revisado_IA` al encontrar PDF.
- **Búsqueda balanceada**: `generar_terminos_busqueda()` genera 4 términos por área (web/SW, IoT, mecánica).

## Política de rutas absolutas (rev 2026-06-03)

Todos los módulos usan rutas absolutas derivadas de `__file__`:

```python
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
```

| Constante | Ruta absoluta canónica |
|---|---|
| `DB_PATH` | `job_hunter/db/vacantes.db` |
| `OUTPUTS_DIR` | `job_hunter/outputs/` |
| `TEMPLATES_DIR` | `job_hunter/latex_templates/` |
| `CONTEXT_DIR` | `job_hunter/context/` (o `PROFILE_BASE_DIR` del `.env`) |

Los archivos `.tex` y `.pdf` generados aterrizan **siempre** en `job_hunter/outputs/`.
Nunca se escriben en la raíz del proyecto.
