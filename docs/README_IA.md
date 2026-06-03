# README â€” Job Hunter

Sistema local de automatizaciÃ³n de bÃºsqueda de empleo: scraping autÃ³nomo â†’ gestiÃ³n Kanban en tiempo real â†’ generaciÃ³n de CV via Claude Desktop (MCP) â†’ editor LaTeX + PDF local.

## Stack

| Capa | TecnologÃ­a | Rol |
|---|---|---|
| Scraping | Playwright + Python | Browser agent anti-bot (Computrabajo, OCC) |
| Backend | FastAPI (puerto 8000) | API REST para datos + PDFs + LaTeX |
| Bot | python-telegram-bot | Control via Telegram con menÃº inline (`/menu`) |
| Frontend | Next.js + Tailwind v4 (puerto 3000) | Dashboard Kanban en tiempo real |
| IA | Claude Desktop + MCP | EvalÃºa compatibilidad, genera `.tex` a medida |
| MCP Server | `mcp_server.py` | 4 tools: get_vacancy_by_id, get_pending_vacancies, update_compatibility, save_latex_cv |
| CompilaciÃ³n | `pdflatex` (MiKTeX) | `.tex` â†’ PDF local en `outputs/` |
| Persistencia | SQLite `vacantes.db` | Ãšnica fuente de verdad |

## Flujo macro

```
POST /scrape (cantidad)
  â†’ browser_agent.py --limit N â†’ vacantes.db
      â†’ Dashboard muestra vacantes nuevas en tiempo real (polling silencioso cada 5 s)
          â†’ "Copiar Prompt MCP" en VacanteCard
              â†’ Claude Desktop:
                  1) get_vacancy_by_id
                  2) evalÃºa perfil + update_compatibility
                  3) genera LaTeX enfocado
                  4) save_latex_cv â†’ pdflatex â†’ Revisado_IA
                      â†’ "Ver PDF" (modal iframe) o "Editar LaTeX" (textarea + recompila)
```

## Estructura

```
Trabajo/
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ PIPELINE_IA.md       # flujo MCP + endpoints LaTeX
â”‚   â”œâ”€â”€ README_IA.md         # este archivo
â”‚   â””â”€â”€ ARQUITECTURA_Y_BD.md
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ dashboard/page.tsx   # Kanban + banner scraping tiempo real
â”‚   â”‚   â”œâ”€â”€ vacantes/page.tsx
â”‚   â”‚   â”œâ”€â”€ plantillas/page.tsx
â”‚   â”‚   â””â”€â”€ perfil/page.tsx
â”‚   â”œâ”€â”€ components/
â”‚   â”‚   â”œâ”€â”€ AddVacanteModal.tsx  # tabs: Manual | JSON | BÃºsqueda autÃ³noma
â”‚   â”‚   â”œâ”€â”€ KanbanBoard.tsx
â”‚   â”‚   â”œâ”€â”€ VacanteCard.tsx      # prompt MCP + modal PDF + modal editor LaTeX
â”‚   â”‚   â””â”€â”€ StatusBadge.tsx
â”‚   â””â”€â”€ lib/api.ts               # mÃ©todos REST + getLatex/saveLatex
â””â”€â”€ job_hunter/
    â”œâ”€â”€ .env                     # GROQ_API_KEY, PROFILE_BASE_DIR (opcional)
    â”œâ”€â”€ context/                 # fallback de perfil
    â”œâ”€â”€ db/vacantes.db
    â”œâ”€â”€ outputs/                 # .tex y .pdf generados
    â””â”€â”€ src/
        â”œâ”€â”€ api.py               # FastAPI — /latex/{id}, /compatibilidad, /perfil, /pdf con CSP
        â”œâ”€â”€ bot.py               # Telegram — /menu con InlineKeyboardMarkup
        â”œâ”€â”€ browser_agent.py     # Playwright --limit N + evaluar_compatibilidad_rapida por vacante
        â”œâ”€â”€ gemini_engine.py     # OUTPUTS_DIR, compilar_pdf, evaluar_compatibilidad_rapida (Groq)
        â”œâ”€â”€ mcp_server.py        # 4 tools MCP; HTTP puro a localhost:8000, sin sqlite directo
        â”œâ”€â”€ reset_db.py          # Hard reset: borra vacantes + outputs/ .tex/.pdf
        â”œâ”€â”€ test_mcp_patch.py    # Valida PATCH status/compatibilidad vía urllib
        â””â”€â”€ init_db.py / migrate_db.py
```

## Arranque (3 terminales)

```powershell
# T1 â€” API
cd job_hunter\src; python api.py

# T2 â€” Bot (opcional)
python bot.py

# T3 â€” Frontend
cd ..\..\frontend; npm run dev
```

El MCP server se registra en `claude_desktop_config.json`, no requiere terminal manual.

## Variables de entorno

| Archivo | Variable | Valor |
|---|---|---|
| `job_hunter/.env` | `GROQ_API_KEY` | Key de console.groq.com (scraper) |
| `job_hunter/.env` | `PROFILE_BASE_DIR` | Ruta al directorio con mi_perfil.md (default: `C:\Users\GIRTEC\Desktop\Trabajo\Trabajo`) |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

## GeneraciÃ³n de CV â€” paso a paso

1. Vacante en **No_Creado** o **Requiere_Correccion** â†’ expandir tarjeta.
2. Click **"Copiar Prompt MCP"** â€” el prompt ultra-minimo de 5 pasos se copia al portapapeles.
3. Pegar en Claude Desktop y enviar.
4. Claude usa `get_vacancy_by_id` â†’ lee reqs.
5. Claude evalÃºa el match con el perfil y llama `update_compatibility`.
6. Claude genera LaTeX enfocado priorizando habilidades mecÃ¡nicas y de automatizaciÃ³n.
7. Claude llama `save_latex_cv` â†’ pdflatex â†’ status `Revisado_IA`.
8. En la tarjeta aparecen **Ver PDF** (modal iframe) y **Editar LaTeX** (editor con recompilaciÃ³n).

## Editor LaTeX

- Abre el `.tex` desde `GET /latex/{id}` en un textarea de pantalla completa.
- Al guardar hace `POST /latex/{id}` con el texto crudo.
- El backend sobrescribe el archivo y ejecuta `pdflatex` en `outputs/`.
- Muestra confirmaciÃ³n verde/roja segÃºn el resultado de compilaciÃ³n.

## Bot de Telegram â€” MenÃº interactivo

El bot expone un menÃº con `InlineKeyboardMarkup` accesible con `/menu`:

| BotÃ³n | AcciÃ³n |
|---|---|
| ðŸ” Buscar Vacantes | Lanza `browser_agent --limit 3` en background |
| ðŸ“‹ Ver Pendientes | Lista vacantes `No_Creado`/`Requiere_Correccion` con botones por vacante |
| âš™ï¸ Resumen | Muestra stats de la DB (total, por status, por compatibilidad) |

Por cada vacante pendiente aparecen botones inline:

| BotÃ³n | `callback_data` | AcciÃ³n |
|---|---|---|
| ðŸš€ Generar | `gen_{id}` | Llama `generar_y_compilar` + audita con Inspector IA |
| ðŸ“„ Descargar PDF | `pdf_{id}` | EnvÃ­a el archivo `outputs/cv_vacante_{id}.pdf` |
| âœ… Marcar Listo | `listo_{id}` | PATCH status â†’ `Listo_Manual` |

Los botones PDF tambiÃ©n aparecen en `/detalles <id>` si el status es `Revisado_IA`.

## Scraping autÃ³nomo

```powershell
python job_hunter/src/browser_agent.py --limit 10
curl -X POST http://localhost:8000/scrape -d "{\"cantidad\":5}" -H "Content-Type: application/json"
```

El dashboard detecta `running: true` en `/scrape/status` y recarga las vacantes cada 5 segundos mostrando un banner animado.

## Regla de contexto

Leer `docs/` antes de proponer cambios al sistema.

## Actualizacion 2026-06-02 (rev 5 — Smart Search)

- `generar_terminos_busqueda()` en `gemini_engine.py`: deriva 12 términos de búsqueda desde `perfil_maestro.json` (sin LLM). Ejemplos para Jair: "Ingeniero IoT", "Embedded Systems Engineer", "SmartCity Developer", "Automatización Industrial".
- `browser_agent.py`: `SEARCH_TERMS` dinámico desde el perfil en tiempo de carga; `--terms` CLI para override.
- `POST /scrape` acepta `terminos: string[]` opcional; si no se envía, usa perfil automáticamente.
- `GET /api/search-terms`: retorna los términos actuales derivados del perfil (fuente: perfil_maestro.json).
- `AddVacanteModal` pestaña "Búsqueda autónoma": carga términos del perfil con checkboxes; usuario selecciona/deselecciona antes de lanzar el scraper.
- Flujo completo autogestionado: edita perfil → guarda → términos se actualizan → búsquedas mejoran.

## Actualizacion 2026-06-02 (rev 4 — SSoT)

- **`data/perfil_maestro.json`** es ahora la única fuente de verdad. Elimina alucinaciones en CVs.
- `GET /api/perfil` + `POST /api/perfil`: carga/guarda el JSON maestro y regenera `mi_perfil.md`.
- Página Perfil: formulario estructurado (datos personales, habilidades, experiencia, educación, proyectos); botón "Guardar" escribe el JSON y regenera el .md.
- Prompt MCP de 4 pasos: apunta directamente a `data/perfil_maestro.json`.
- `evaluar_compatibilidad_rapida`: lee perfil_maestro.json (estructura) en vez de md plano.
- Dashboard: polling 3 s.

## Actualizacion 2026-06-02 (rev 3)

- Hard reset ejecutado: 0 vacantes, 0 archivos en outputs/.
- `POST /vacantes` y `POST /vacantes/bulk`: llaman a `evaluar_compatibilidad_rapida` on-the-fly y guardan el nivel en `compatibilidad` al insertar.
- `mcp_server._save_latex_cv`: PATCH → `En_Proceso` al inicio; PATCH → `Revisado_IA` al finalizar con PDF. Sin acceso directo a .db.
- Dashboard: polling vacantes cada 2 s (antes 3 s).
- `VacanteCard`: spinner `Loader2` junto al título cuando `status === 'En_Proceso'`; tarjeta se mueve sola al columna Revisado_IA con el siguiente tick de polling.
- Prompt MCP reducido a 4 pasos: get_vacancy_by_id → update_compatibility → CV LaTeX → save_latex_cv.

## Actualizacion 2026-06-02 (rev 2)

- Dashboard: polling de vacantes a 3 s (antes 5 s); scraper status sigue en 3 s.
- `VacanteCard`: prompt MCP actualizado con 5 pasos anti-alucinación (lee mi_perfil.md real, prohíbe corchetes, integra foto si hay plantilla).
- `GET /pdf/{id}`: añadidos `X-Frame-Options: SAMEORIGIN` y `Content-Security-Policy: frame-ancestors 'self' http://localhost:3000` para corregir "refused to connect" en iframe.
- `POST /perfil/upload` + `GET /perfil`: extrae texto de PDF (PyPDF2) o guarda .md/.txt en `CONTEXT_DIR/mi_perfil.md`.
- `frontend/app/perfil/page.tsx`: reemplazado mock por vista real con upload y preview.
- `gemini_engine.evaluar_compatibilidad_rapida`: evalúa match vacante-candidato con Groq (max 10 tokens).
- `browser_agent.py`: llama a `evaluar_compatibilidad_rapida` tras cada insert exitoso y actualiza el campo `compatibilidad` antes de retornar.
- `src/reset_db.py`: script de hard reset con diagnóstico previo (borrar vacantes + outputs/).
- `src/test_mcp_patch.py`: test de PATCH status y compatibilidad vía urllib (sin sqlite directo).

