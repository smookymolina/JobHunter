Job Hunter

Sistema local para automatizar busqueda de empleo, generar CVs en LaTeX y coordinar el flujo IA sobre SQLite.

Leer primero:
- docs/README_IA.md
- docs/ARQUITECTURA_Y_BD.md
- docs/PIPELINE_IA.md

Componentes:
- job_hunter/: backend, pipeline, DB, scripts
- frontend/: app Next.js
- docs/: contexto maestro para IAs
- job_hunter/db/vacantes.db: fuente de verdad

Flujo:
vacante -> SQLite -> API -> MCP/IA -> .tex -> pdflatex -> PDF -> Revisado_IA
