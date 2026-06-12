# Arquitectura y Base de Datos

> Última actualización: 2026-06-11 (rev 15 — lazy search terms, compact compat profile cache)

## Stack

| Capa | Tecnología | Puerto |
|---|---|---|
| Backend | FastAPI + Uvicorn (Python 3.13) | 8000 |
| Frontend | Next.js 16 + React 19 + Tailwind 4 (TypeScript) | 3000 |
| Base de datos | PostgreSQL (pg8000) | 5432 |
| IA | Groq API (llama-3.3-70b-versatile) vía cliente openai-compatible | — |
| MCP | `job_hunter/src/mcp_server.py` para Claude Desktop | — |

## Base de Datos — PostgreSQL

### Tabla `usuarios`

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | SERIAL | PK |
| `user_id` | VARCHAR(50) | UNIQUE NOT NULL |
| `email` | VARCHAR(255) | UNIQUE NOT NULL |
| `hashed_password` | TEXT | NOT NULL |
| `created_at` | TIMESTAMP | default NOW() |

- **Seed inicial**: `test@jobhunter.com` / `jobhunter123` → `user_id='default_user'` (preserva 33 vacantes migradas).
- Registro de nuevos usuarios vía `POST /auth/register` → genera `user_id = uuid4().hex`.
- Al crear usuario se genera automáticamente `job_hunter/data/{user_id}_perfil.json`.

### Tabla `vacantes`

| Columna | Tipo | Restricción / Default |
|---|---|---|
| `id` | SERIAL | PK |
| `user_id` | VARCHAR(50) | NOT NULL DEFAULT 'default_user' |
| `titulo` | TEXT | NOT NULL |
| `empresa` | TEXT | nullable |
| `enlace` | TEXT | UNIQUE |
| `requerimientos` | TEXT | nullable |
| `compatibilidad` | TEXT | default 'Nula' |
| `status` | TEXT | default 'No_Creado' |
| `fecha_registro` | TIMESTAMP | default NOW() |
| `fecha_postulacion` | TIMESTAMP | nullable — se llena al marcar `Listo_Manual` |
| `favorito` | INTEGER | default 0 |

### Tabla `vacantes_eliminadas` (blacklist)

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | SERIAL | PK |
| `user_id` | VARCHAR(50) | NOT NULL DEFAULT 'default_user' |
| `enlace` | TEXT | NOT NULL |
| `titulo` | TEXT | nullable |
| `fecha_eliminacion` | TIMESTAMP | default NOW() |
| — | UNIQUE | `(user_id, enlace)` |

## Aislamiento multi-tenant y Seguridad

- **Base de Datos**: Cada registro incluye `user_id` para filtrado estricto a nivel de consulta.
- **Archivos**: Los PDFs y archivos `.tex` se guardan en `job_hunter/outputs/{user_id}/`, asegurando que un usuario no pueda acceder a los documentos de otro.
- **Telegram**: El token del bot se almacena cifrado con **Fernet (AES-128)** en la tabla `usuarios`. Solo es accesible tras validar la contraseña del usuario.
- **Scraper**: `browser_agent.py` opera de forma aislada, insertando vacantes vía API para respetar las reglas de negocio y blacklist.

## Máquina de estados

```
No_Creado → En_Proceso → Revisado_IA → Listo_Manual → Entrevista
                      ↘ Requiere_Correccion → (regenerar)
```

| Estado | Lo activa | Notas |
|---|---|---|
| `No_Creado` | Alta nueva | Estado inicial |
| `En_Proceso` | Inicio de `generar_y_compilar()` | Spinner en tarjeta |
| `Requiere_Correccion` | Inspector rechaza / pdflatex falla | |
| `Revisado_IA` | Inspector aprueba (con PDF) | Habilita Ver PDF / Editar LaTeX |
| `Listo_Manual` | PATCH manual / comando bot | Registra `fecha_postulacion` |
| `Entrevista` | PATCH manual / comando bot | Estado de entrevista activa |

> **Regla del watcher**: `_sync_one` en `watcher.py` nunca sobreescribe `Listo_Manual`.

## Frontend — Dashboard (`/dashboard`)

Vista dual controlada por `activeFilter: Status | null`:

| `activeFilter` | Vista renderizada |
|---|---|
| `null` | **Kanban** — columnas horizontales scrollables, columnas dinámicas ocultas si vacías |
| `Status` activo | **Lista/Tabla** — filas planas con ID, Puesto, Empresa, Compat., Status, Fecha, Enlace |

- Las **tarjetas KPI** superiores son botones: click activa el filtro (click de nuevo lo desactiva).
- Orden en ambas vistas: favorito desc → compatibilidad desc (Alta→Media→Baja→Nula) → id desc.
- Botón "Ver tablero completo" en la vista Lista regresa al Kanban.

## Motor de CV / LLM (`gemini_engine.py`)

- **`_load_profile_json(user_id)`** — helper DRY: carga JSON del usuario → fallback `perfil_maestro.json` → `None`.
- **`_get_user_profile(user_id)`** — string detallado para el `user_msg` (nombre, título, resumen, habilidades, experiencia con logros).
- **`_get_user_profile_structured(user_id)`** — devuelve `{nombre, resumen, skills[], experiencia_str}` para inyección dinámica en el system prompt.
- **`generar_latex_cv(vacante_id, user_id)`** — `system_msg` maestro de 5 secciones dinámicas:

| Sección | Contenido |
|---|---|
| PERFIL DEL CANDIDATO | `resumen` + `skills` interpolados desde BD en runtime |
| TONO Y ESTILO | Ejecutivo, verbos de acción, sin clichés |
| ANTI-ALUCINACIÓN | Solo habilidades/experiencias del perfil real; no copiar frases del anuncio |
| ANTI-COPY DE TÍTULO | Sintetizar título orgánico, nunca copiar el de la vacante |
| PROTECCIÓN LaTeX | Escapar %, &, $, #, _; sin Markdown dentro del bloque |

## Scraper (`browser_agent.py`)

- **Términos lazy**: `generar_terminos_busqueda()` ya NO se llama a nivel de módulo. Se evalúa dentro de `main()` solo si no se reciben `--terms` por CLI. Cuando la API lanza el subprocess, siempre pasa los términos calculados, evitando la conexión a BD en el arranque del subprocess.
- **`_passes_geo_filter(titulo, reqs, filtros)`** — post-validación geográfica antes de `_post_vacante`. Usa `unicodedata.normalize('NFD')` para comparación sin acentos. Pasa automáticamente si `ubicacion` está vacío o `modalidad == 'remoto'`. Activo en: Computrabajo, OCC, Indeed, Bumeran, LinkedIn. Remotive exento (plataforma 100% remota).
- Filtros en cadena por vacante: texto/modalidad → salario → **geo** → insertar.

## Motor de compatibilidad (`evaluar_compatibilidad_rapida`)

- Usa perfil compacto: título profesional + primeros 30 skills (~150 chars) en lugar del perfil completo (~1000 chars).
- Perfil cacheado como variable de módulo (`_COMPAT_PROFILE_CACHE`) → 0 lecturas de disco tras la primera llamada en el proceso de la API.
- Requerimientos truncados a 1200 chars (antes 2000). Ahorro aprox. 290 tokens por evaluación.

## Endpoints — `src/api.py` (puerto 8000)

### Auth (públicos — sin JWT)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Retorna `{access_token, token_type, user_id}` |
| POST | `/auth/register` | Crea usuario + perfil JSON. Retorna 201 o 400 si email duplicado |

### Vacantes (requieren JWT)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/vacantes` | Lista; acepta `?limit=` y `?status=` |
| GET | `/vacantes/{id}` | Detalle completo |
| PATCH | `/vacantes/{id}/status` | Cambia status |
| PATCH | `/vacantes/{id}/compatibilidad` | Cambia compatibilidad |
| PATCH | `/vacantes/{id}/favorito` | Toggle favorito |
| POST | `/vacantes` | Crea vacante (usa `get_optional_user`) |
| POST | `/vacantes/bulk` | Importa lista JSON (usa `get_optional_user`) |
| DELETE | `/vacantes/{id}` | Borra vacante → agrega a blacklist |
| GET | `/vacantes/eliminadas` | Lista blacklist |
| DELETE | `/vacantes/eliminadas/{id}` | Restaura entrada de blacklist |

### CV / LaTeX (requieren JWT)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/latex/{id}` | Devuelve `.tex` como texto plano |
| POST | `/latex/{id}` | Body: LaTeX crudo → sobrescribe y recompila |
| POST | `/generar_cv/{id}` | Genera CV con Groq+LaTeX, audita con Inspector IA |
| GET | `/pdf/{id}` | PDF inline o `?download=true` |
| GET | `/download/cv/{id}` | Descarga protegida con validación de ownership |
| POST | `/vacantes/{id}/sync` | Sincroniza status con archivos generados |

### Perfil (requieren JWT)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/perfil` | Retorna `{user_id}_perfil.json` del usuario autenticado |
| POST | `/api/perfil` | Guarda `{user_id}_perfil.json` y regenera `mi_perfil.md` |
| POST | `/perfil/upload` | Sube PDF/.md/.txt → combina en `mi_perfil.md` (global) |
| GET | `/perfil` | Devuelve contenido de `mi_perfil.md` (global) |

### Misc

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/scrape` | Lanza browser_agent con `{cantidad, terminos, filtros}` |
| GET | `/scrape/status` | Estado del scraping activo |
| POST | `/upload_template` | Sube `mi_estilo.tex` |
| GET | `/template/activa` | Informa qué plantilla está activa |
| DELETE | `/template/custom` | Elimina plantilla personalizada |
| GET | `/template/download` | Descarga plantilla activa |
| GET | `/api/search-terms` | Términos de búsqueda del perfil |
| GET | `/debug/sync-health` | Snapshot del watcher (dry-run) |
| POST | `/debug/sync-health` | Ejecuta sync real |

## Notas operativas

- Outputs por usuario: `job_hunter/outputs/{user_id}/cv_vacante_{id}.tex` y `.pdf`.
- Auto-migración al arrancar: `lifespan` en `api.py` crea todas las tablas y el seed `default_user` si no existen.
- El watcher DeepHealthWatcher corre cada 20 s en background y sincroniza estados.
