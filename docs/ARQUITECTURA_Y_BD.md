# Arquitectura y Base de Datos

> Última actualización: 2026-06-07 (rev 12 — Multi-tenant Auth + Register flow)

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

## Aislamiento multi-tenant

- Cada usuario solo ve y opera sobre sus propias vacantes (`WHERE user_id=%s`).
- Perfiles JSON aislados por usuario: `job_hunter/data/{user_id}_perfil.json`.
- Outputs de PDF/LaTeX aislados: `job_hunter/outputs/{user_id}/`.
- La blacklist también está aislada por `user_id`.
- `get_optional_user` en `POST /vacantes` y `POST /vacantes/bulk` permite al scraper (`browser_agent.py`) escribir sin JWT, usando `user_id='default_user'`.

## Máquina de estados

```
No_Creado → En_Proceso → Revisado_IA → Listo_Manual (terminal)
                      ↘ Requiere_Correccion → (regenerar)
```

| Estado | Lo activa | Notas |
|---|---|---|
| `No_Creado` | Alta nueva | Estado inicial |
| `En_Proceso` | Inicio de `generar_y_compilar()` | Spinner en tarjeta |
| `Requiere_Correccion` | Inspector rechaza / pdflatex falla | |
| `Revisado_IA` | Inspector aprueba (con PDF) | Habilita Ver PDF / Editar LaTeX |
| `Listo_Manual` | PATCH manual / comando bot | **Terminal** — registra `fecha_postulacion` |

> **Regla del watcher**: `_sync_one` en `watcher.py` nunca sobreescribe `Listo_Manual`.

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
