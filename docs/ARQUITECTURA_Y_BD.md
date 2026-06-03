# Arquitectura y Base de Datos

## Esquema SQLite â€” tabla `vacantes`

| Columna | Tipo | RestricciÃ³n / Default |
|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT |
| `titulo` | TEXT | NOT NULL |
| `empresa` | TEXT | nullable |
| `enlace` | TEXT | UNIQUE |
| `requerimientos` | TEXT | nullable |
| `compatibilidad` | TEXT | CHECK('Alta','Media','Baja','Nula') Â· default 'Nula' |
| `status` | TEXT | CHECK(ver estados) Â· default 'No_Creado' |
| `fecha_registro` | TEXT | default datetime('now') |

## MÃ¡quina de estados

```
No_Creado â†’ En_Proceso â†’ Revisado_IA â†’ Listo_Manual
                      â†˜ Requiere_Correccion â†’ (regenerar)
```

| Estado | Lo activa |
|---|---|
| `No_Creado` | Alta nueva, error de pipeline |
| `En_Proceso` | Inicio de `generar_y_compilar()` |
| `Requiere_Correccion` | Inspector rechaza el CV |
| `Revisado_IA` | Inspector aprueba (con o sin PDF) |
| `Listo_Manual` | PATCH manual / comando bot |

## Endpoints â€” `src/api.py` (puerto 8000)

| MÃ©todo | Ruta | DescripciÃ³n |
|---|---|---|
| GET | `/vacantes` | Lista; acepta `?limit=` y `?status=` |
| GET | `/vacantes/{id}` | Detalle completo |
| PATCH | `/vacantes/{id}/status` | Cambia status â€” body `{"status": "..."}` |
| PATCH | `/vacantes/{id}/compatibilidad` | Cambia compatibilidad â€” body `{"compatibilidad": "..."}` |
| POST | `/vacantes` | Crea vacante manual |
| POST | `/vacantes/bulk` | Importa lista JSON |
| DELETE | `/vacantes/{id}` | Borra vacante |
| GET | `/latex/{id}` | Devuelve `.tex` como texto plano |
| POST | `/latex/{id}` | Body: LaTeX crudo â†’ sobrescribe y recompila |
| POST | `/generar_cv/{id}` | Genera CV con Groq+LaTeX, audita con Inspector IA, retorna aprobado/rechazado |
| POST | `/scrape` | Lanza browser_agent con `{"cantidad": N}` |
| GET | `/scrape/status` | Estado del scraping activo |
| GET | `/pdf/{id}` | PDF inline o `?download=true` |
| POST | `/upload_template` | Sube `mi_estilo.tex` |
| GET | `/template/activa` | Informa qué plantilla está activa |
| POST | `/perfil/upload` | Sube uno o varios PDF/.md/.txt (`files[]`) → combina texto en mi_perfil.md |
| GET | `/perfil` | Devuelve contenido de mi_perfil.md como JSON |

## Notas operativas

- GeneraciÃ³n de CVs: Human-in-the-loop via Claude Desktop + MCP (ver `PIPELINE_IA.md`).
- Archivos de salida en `job_hunter/outputs/` (`cv_vacante_{id}.tex` y `.pdf`).
- MigraciÃ³n de schema: `python src/migrate_db.py` (ya aplicada).


## Actualizacion 2026-06-03 (rev 8 — Rutas Absolutas + Hard Reset)

- **Política de rutas absolutas**: todos los módulos (`gemini_engine.py`, `init_db.py`, `reset_db.py`, `api.py`) usan `os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ...))`. Garantiza rutas correctas sin importar el CWD al lanzar el proceso.
- **Archivos de salida**: `.tex` y `.pdf` se escriben **siempre** en `job_hunter/outputs/`. Nunca en la raíz.
- **Hard Reset validado**: `reset_db.py` borra `db/vacantes.db`, limpia `outputs/` y recrea el schema con `CREATE TABLE vacantes` fresco.
- **Organización de scripts**: scripts de debug/test (`check_db.py`, `debug_*.py`, etc.) movidos a `job_hunter/src/`.
- **Validación E2E** confirmada: `POST /vacantes` → `GET /vacantes` → `POST /generar_cv/1` → PDF en `job_hunter/outputs/cv_vacante_1.pdf`, raíz limpia.

## Actualizacion 2026-06-03 (rev 7 — API-First Sync)

- **`browser_agent.py` ya no toca SQLite**. Cada vacante encontrada se envía via `POST /vacantes` a la API (API_BASE_URL en `.env`). Elimina bloqueos WAL y garantiza que el frontend reciba los datos en tiempo real.
- **`POST /generar_cv/{vid}`**: nuevo endpoint para que el bot genere CVs sin importar `gemini_engine` directamente. Flujo: `En_Proceso → generar_y_compilar → evaluar_cv → Revisado_IA / Requiere_Correccion`.
- `GET /vacantes` y `GET /scrape/status` → header `Cache-Control: no-store`.
- `GET /vacantes` registra en consola el número de filas retornadas (`_log.info`).
- Dashboard polling reducido a **2 s**.
- Bot: `_cb_generar` y `_cb_genall` usan `POST /generar_cv/{vid}` en lugar de imports directos.
- Bot: todas las acciones (marcar listo, borrar, generar) incluyen botón **◀️ Menú Principal**.

## Actualizacion 2026-06-02 (rev 5 — Smart Search)

- `GET /api/search-terms`: términos derivados de `perfil_maestro.json` sin LLM.
- `POST /scrape` acepta `{"cantidad": N, "terminos": [...]}` — los términos son opcionales (default: perfil).
- `browser_agent.py`: `SEARCH_TERMS` dinámico al arrancar; acepta `--terms` para override desde CLI o API.
- `generar_terminos_busqueda()`: genera 12 términos por keywords del perfil (IoT, mecánica, full-stack, etc.).

## Actualizacion 2026-06-02 (rev 4 — SSoT)

- **`data/perfil_maestro.json`**: fuente de verdad única para datos personales, habilidades, experiencia, educación y proyectos.
- `GET /api/perfil` → retorna perfil_maestro.json; `POST /api/perfil` → valida, guarda y regenera mi_perfil.md automáticamente.
- `evaluar_compatibilidad_rapida` lee perfil_maestro.json (SSoT) con fallback a mi_perfil.md.
- Página Perfil reemplazada por formulario estructurado (sin upload de PDF); cada guardado regenera mi_perfil.md.
- Prompt MCP apunta a `job_hunter/data/perfil_maestro.json` para datos exactos sin alucinaciones.
- Dashboard polling: 3 s.

## Actualizacion 2026-06-02 (rev 2)

- `GET /vacantes` devuelve `requerimientos` para contrato consistente frontend ↔ backend.
- Dashboard polling vacantes: 3 s (antes 5 s).
- `GET /pdf/{id}` devuelve `X-Frame-Options: SAMEORIGIN` + CSP para iframe en modal.
- Nuevos endpoints: `POST /perfil/upload` (PyPDF2 extrae texto → mi_perfil.md) y `GET /perfil`.
- `save_latex_cv` en MCP reporta HTTP code + body en errores PATCH.
- `browser_agent.py` evalúa compatibilidad con Groq tras cada vacante insertada.
- Nuevos scripts: `src/reset_db.py` (hard reset con diagnóstico) y `src/test_mcp_patch.py` (valida HTTP PATCH).
