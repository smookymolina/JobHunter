# Arquitectura y Base de Datos

## Esquema SQLite — tabla `vacantes`

| Columna | Tipo | Restricción / Default |
|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT |
| `titulo` | TEXT | NOT NULL |
| `empresa` | TEXT | nullable |
| `enlace` | TEXT | UNIQUE |
| `requerimientos` | TEXT | nullable |
| `compatibilidad` | TEXT | CHECK('Alta','Media','Baja','Nula') · default 'Nula' |
| `status` | TEXT | CHECK(ver estados) · default 'No_Creado' |
| `fecha_registro` | TEXT | default datetime('now','localtime') |
| `fecha_postulacion` | TEXT | nullable — se llena automáticamente al marcar `Listo_Manual` |

## Tabla `vacantes_eliminadas` (blacklist)

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | INTEGER | PK AUTOINCREMENT |
| `enlace` | TEXT | UNIQUE NOT NULL |
| `titulo` | TEXT | nullable |
| `fecha_eliminacion` | TEXT | default CURRENT_TIMESTAMP |

Cualquier vacante eliminada vía `DELETE /vacantes/{id}` queda registrada aquí. El scraper y los endpoints de inserción consultan esta tabla antes de insertar; si el enlace está en la blacklist se rechaza con 409 y nunca reaparece.

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
| `Listo_Manual` | PATCH manual / comando bot | **Terminal** — el watcher no lo revierte; registra `fecha_postulacion` |

> **Regla del watcher**: `_sync_one` en `watcher.py` nunca sobreescribe `Listo_Manual`. Solo corrige estados `No_Creado`/`En_Proceso`/`Requiere_Correccion` donde hay PDF generado.

## Endpoints — `src/api.py` (puerto 8000)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/vacantes` | Lista; acepta `?limit=` y `?status=` |
| GET | `/vacantes/{id}` | Detalle completo (incluye `fecha_postulacion`) |
| PATCH | `/vacantes/{id}/status` | Cambia status; si es `Listo_Manual` guarda `fecha_postulacion` |
| PATCH | `/vacantes/{id}/compatibilidad` | Cambia compatibilidad |
| POST | `/vacantes` | Crea vacante manual (chequea blacklist) |
| POST | `/vacantes/bulk` | Importa lista JSON (omite entradas en blacklist) |
| DELETE | `/vacantes/{id}` | Borra vacante y la agrega a blacklist |
| GET | `/latex/{id}` | Devuelve `.tex` como texto plano |
| POST | `/latex/{id}` | Body: LaTeX crudo → sobrescribe y recompila |
| POST | `/generar_cv/{id}` | Genera CV con Groq+LaTeX, audita con Inspector IA |
| POST | `/scrape` | Lanza browser_agent con `{"cantidad": N, "terminos": [...]}` |
| GET | `/scrape/status` | Estado del scraping activo |
| GET | `/pdf/{id}` | PDF inline o `?download=true` |
| POST | `/upload_template` | Sube `mi_estilo.tex` |
| GET | `/template/activa` | Informa qué plantilla está activa |
| POST | `/perfil/upload` | Sube PDF/.md/.txt → combina texto en mi_perfil.md |
| GET | `/perfil` | Devuelve contenido de mi_perfil.md |
| GET | `/api/perfil` | Retorna perfil_maestro.json |
| POST | `/api/perfil` | Valida, guarda perfil_maestro.json y regenera mi_perfil.md |
| GET | `/api/search-terms` | Términos de búsqueda derivados del perfil |

## Notas operativas

- Generación de CVs: Human-in-the-loop via Claude Desktop + MCP (ver `PIPELINE_IA.md`).
- Archivos de salida en `job_hunter/outputs/` (`cv_vacante_{id}.tex` y `.pdf`).
- Auto-migración al arrancar la API: `lifespan` en `api.py` crea la tabla blacklist y agrega `fecha_postulacion` si no existen.

## Actualización 2026-06-04 (rev 9 — Blacklist + Postulación + Search fix)

- **Blacklist de eliminadas**: `DELETE /vacantes/{id}` guarda el enlace en `vacantes_eliminadas`. `POST /vacantes` y `POST /vacantes/bulk` rechazan entradas en blacklist. La vacante nunca reaparece en scrapes futuros.
- **fecha_postulacion**: al marcar `Listo_Manual`, la API registra automáticamente la fecha/hora de postulación. El frontend muestra "CV enviado — esperando respuesta de la empresa · Postulado el YYYY-MM-DD HH:MM".
- **Watcher bugfix**: `_sync_one` en `watcher.py` ahora salta vacantes con status `Listo_Manual` en lugar de revertirlas a `Revisado_IA` cuando existe un PDF.
- **`generar_terminos_busqueda()` balanceado**: 4 términos por área (SW/web primero, luego IoT/embebidos, luego mecánica). Con el perfil actual: `Desarrollador Full Stack, Full Stack Developer, Desarrollador Python, Desarrollador React, Desarrollador IoT, Ingeniero Sistemas Embebidos, Automatización Industrial, Desarrollador Firmware IoT, Ingeniero Mecánico, Ingeniero Mecatrónico, Ingeniero CAD CAE, Ingeniero Control Automático`.

## Actualización 2026-06-03 (rev 8 — Rutas Absolutas)

- Política de rutas absolutas: todos los módulos usan `os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ...))`.
- Hard Reset validado: `reset_db.py` borra DB, limpia `outputs/` y recrea el schema.
- Validación E2E: `POST /vacantes` → `POST /generar_cv/1` → PDF en `job_hunter/outputs/`.
