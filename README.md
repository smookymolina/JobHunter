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
- El listado `/vacantes` devuelve `requerimientos` de forma consistente.
- El dashboard hace auto-refresco silencioso cada 5 segundos.
- El prompt MCP de la tarjeta es minimo y directo para ahorrar tokens.
