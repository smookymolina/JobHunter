# Pipeline IA — Job Hunter

## Actualizacion 2026-06-03 (rev 9 — Dedup estricta + Compatibilidad centralizada)

- **Deduplicación estricta en `POST /vacantes`**: `SELECT enlace` antes del INSERT → HTTP 409 limpio si ya existe. Elimina la carrera entre `INSERT OR IGNORE` y `changes()`.
- **Compatibilidad evaluada en la API**: `evaluar_compatibilidad_rapida(reqs)` se invoca en `POST /vacantes` si el payload no trae `Alta/Media/Baja` explícito. Lee `perfil_maestro.json` (SSoT). Esto centraliza la lógica: ningún scraper necesita calcular compat por su cuenta.
- **`browser_agent._post_vacante()`**: captura 409 y loguea `”Saltando duplicado: <titulo>”` sin abortar el proceso.
- **`bot._api_sync()`**: captura 409 silenciosamente y retorna el body del response.

---

# Pipeline IA — Human-in-the-Loop vía MCP

La generación de CVs es un proceso **impulsado por el usuario** con Claude Desktop como motor de IA.
La API sirve datos, PDFs estáticos y acepta actualizaciones vía REST.

## Flujo completo

```
Usuario abre VacanteCard (No_Creado / Requiere_Correccion)
  â””â”€ Click "Copiar Prompt MCP"
       â””â”€ portapapeles recibe el prompt con el ID exacto
            â””â”€ Usuario pega en Claude Desktop
                 â”œâ”€ 1) get_vacancy_by_id(id)   â†’ titulo/empresa/enlace/reqs desde API
                 â”œâ”€ 2) Lee perfil desde C:\Users\GIRTEC\Desktop\Trabajo\Trabajo\
                 â”œâ”€ 3) update_compatibility(id, nivel)  â†’ PATCH /vacantes/{id}/compatibilidad
                 â”œâ”€ 4) Genera LaTeX priorizando skills mecÃ¡nicos y de automatizaciÃ³n
                 â””â”€ 5) save_latex_cv(id, latex_code)
                          â”œâ”€ Escribe outputs/cv_vacante_{id}.tex
                          â”œâ”€ pdflatex â†’ outputs/cv_vacante_{id}.pdf
                          â””â”€ PATCH /vacantes/{id}/status â†’ Revisado_IA
```

## Herramientas MCP (`src/mcp_server.py`)

| Tool | ParÃ¡metros | ImplementaciÃ³n |
|---|---|---|
| `get_vacancy_by_id` | `vacante_id: int` | GET `/vacantes/{id}` via urllib |
| `get_pending_vacancies` | â€” | GET `/vacantes?limit=100` + filtro Python |
| `update_compatibility` | `vacante_id: int`, `nivel: str` | PATCH `/vacantes/{id}/compatibilidad` via urllib |
| `save_latex_cv` | `vacante_id: int`, `tex_content: str` | Escribe .tex + pdflatex + PATCH `/vacantes/{id}/status` |

**Bypass de sandbox**: todas las escrituras/lecturas a SQLite se reemplazaron por llamadas HTTP a `http://localhost:8000`. Solo `compilar_pdf` accede a disco directamente (necesario para pdflatex). Los errores HTTP se loggean con el body completo del response para diagnÃ³stico.

## Editor LaTeX en Frontend

Para vacantes en `Revisado_IA`, la tarjeta muestra:
- **Ver PDF** â†’ Modal con `<iframe src="/pdf/{id}">`
- **Editar LaTeX** â†’ Modal con `<textarea>` cargado desde `GET /latex/{id}`; al guardar hace `POST /latex/{id}` y recompila.

## API endpoints para LaTeX (`src/api.py`)

| MÃ©todo | Ruta | DescripciÃ³n |
|---|---|---|
| GET | `/latex/{id}` | Devuelve `.tex` como `text/plain` |
| POST | `/latex/{id}` | Body: texto LaTeX crudo â†’ sobrescribe y recompila |
| PATCH | `/vacantes/{id}/compatibilidad` | `{"compatibilidad": "Alta\|Media\|Baja\|Nula"}` |

## Dashboard en tiempo real

`app/dashboard/page.tsx` hace polling a `GET /scrape/status` cada 5 segundos.
Cuando `running === true`:
- Muestra banner animado: "Buscando vacantes de forma autÃ³noma..."
- Activa un `setInterval` de 3 s que recarga la lista de vacantes automÃ¡ticamente.

## Endpoints de scraping

| MÃ©todo | Ruta | Body / Resp |
|---|---|---|
| POST | `/scrape` | `{"cantidad": N}` â†’ lanza browser_agent |
| GET | `/scrape/status` | `{"running": bool, "last": "..."}` |

## API completa (datos + archivos)

| MÃ©todo | Ruta | DescripciÃ³n |
|---|---|---|
| GET | `/vacantes` | Lista vacantes |
| GET | `/vacantes/{id}` | Detalle completo |
| POST | `/vacantes` | Crear manual |
| POST | `/vacantes/bulk` | InserciÃ³n masiva |
| PATCH | `/vacantes/{id}/status` | Cambiar status |
| PATCH | `/vacantes/{id}/compatibilidad` | Cambiar compatibilidad |
| DELETE | `/vacantes/{id}` | Borrar vacante |
| GET | `/pdf/{id}` | PDF compilado (inline o `?download=true`) |
| GET | `/latex/{id}` | CÃ³digo LaTeX en texto plano |
| POST | `/latex/{id}` | Sobrescribir + recompilar |
| POST | `/upload_template` | Subir plantilla .tex |
| GET | `/template/activa` | Plantilla activa |
| POST | `/perfil/upload` | Sube PDF/.md/.txt → extrae texto a mi_perfil.md |
| GET | `/perfil` | Devuelve contenido de mi_perfil.md |

## Actualizacion 2026-06-02 (rev 5 — Smart Search)

- `generar_terminos_busqueda()`: 12 términos del perfil sin LLM (ESP32→"Embedded Systems", SmartCity→"SmartCity Developer", etc.).
- `AddVacanteModal` "Búsqueda autónoma": muestra términos del perfil como checkboxes; el usuario selecciona cuáles usar antes de lanzar el scraper.
- Ciclo cerrado: Perfil web → JSON → términos → scraper → vacantes compatibles.

## Actualizacion 2026-06-02 (rev 4 — SSoT)

- Prompt MCP paso 2: apunta a `data/perfil_maestro.json` (JSON estructurado) en vez de mi_perfil.md.
- `GET /api/perfil` + `POST /api/perfil`: endpoints para leer/escribir el JSON maestro.
- `_regenerate_mi_perfil`: al guardar desde el formulario, se regenera `mi_perfil.md` automáticamente como copia de texto.
- Formulario Perfil: reemplaza el upload de PDF — el usuario edita sus datos directamente en la web, eliminando la cadena PDF→OCR→md que causaba alucinaciones.

## Actualizacion 2026-06-02 (rev 3)

- `save_latex_cv` (MCP): PATCH → `En_Proceso` al inicio + PATCH → `Revisado_IA` al finalizar. Cero acceso directo a SQLite.
- `POST /vacantes` + `POST /vacantes/bulk`: evalúan compatibilidad con Groq on-the-fly y la persisten al insertar.
- Dashboard: polling cada 2 s → tarjetas se mueven automáticamente al cambiar de columna.
- `VacanteCard`: spinner azul en título cuando `En_Proceso`.
- Prompt MCP reducido a 4 pasos (sin paso de foto, más compacto).

## Actualizacion 2026-06-02 (rev 2)

- Prompt MCP (5 pasos): paso 2 lee `mi_perfil.md` real, prohíbe corchetes/datos falsos; paso 3 integra foto si hay plantilla.
- Dashboard refresca vacantes cada 3 s (antes 5 s).
- `GET /pdf/{id}` añade X-Frame-Options + CSP para que el iframe en modal funcione desde localhost:3000.
- Sistema de perfil: `POST /perfil/upload` (extrae PDF con PyPDF2 → mi_perfil.md) + `GET /perfil` + página de perfil funcional.
- `browser_agent.py` llama a `evaluar_compatibilidad_rapida` (Groq, max 10 tokens) tras cada insert y persiste el resultado en la DB.

