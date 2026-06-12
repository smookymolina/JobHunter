# README — Job Hunter

Sistema local de automatización de búsqueda de empleo: scraping autónomo → gestión Kanban en tiempo real → generación de CV vía Groq (Llama 3.3 70B) + MCP → editor LaTeX + PDF local.

## Stack

| Capa | Tecnología | Rol |
|---|---|---|
| Scraping | Playwright + Python | Browser agent anti-bot (Computrabajo, OCC, Indeed, Bumeran, LinkedIn, Remotive, GetOnBrd) |
| Backend | FastAPI + Uvicorn (Python 3.13) | API REST para datos + PDFs + LaTeX (puerto 8000) |
| Bot | python-telegram-bot | Control vía Telegram con menú inline (`/menu`) |
| Frontend | Next.js 16 + React 19 + Tailwind 4 (TypeScript) | Dashboard Kanban en tiempo real (puerto 3000) |
| IA | Groq API (llama-3.3-70b-versatile) | CV LaTeX, evaluación de compatibilidad |
| MCP | `mcp_server.py` | 6 tools para Claude Desktop |
| Compilación | `pdflatex` (MiKTeX) | `.tex` → PDF en `outputs/` |
| Persistencia | PostgreSQL (pg8000) | Única fuente de verdad |

## Flujo macro

```
POST /scrape (cantidad, términos opcionales, filtros)
  → browser_agent.py --limit N --terms [...] --filtros {...}
      → vacantes insertadas vía POST /vacantes (con compatibilidad Groq on-the-fly)
          → Dashboard muestra vacantes nuevas (polling cada 2 s)
              → "Generar CV" (one-click) o "Copiar Prompt MCP" para Claude Desktop
                  → pdflatex → PDF disponible en "Ver PDF" / "Editar LaTeX"
```

## Estructura principal

```
JobHunter/
├── docs/
│   ├── PIPELINE_IA.md         # flujo CV + endpoints LaTeX
│   ├── README_IA.md           # este archivo
│   ├── ARQUITECTURA_Y_BD.md   # BD, endpoints, máquina de estados
│   └── AUDIT_MEJORAS.md
├── frontend/
│   ├── app/
│   │   ├── dashboard/page.tsx   # Kanban dual-view + banner scraping
│   │   ├── perfil/page.tsx
│   │   └── plantillas/page.tsx
│   └── components/
│       ├── AddVacanteModal.tsx  # tabs: Manual | JSON masivo | Búsqueda autónoma
│       ├── KanbanBoard.tsx
│       └── VacanteCard.tsx      # modal PDF + editor LaTeX + prompt MCP
└── job_hunter/
    ├── .env                     # GROQ_API_KEY, DATABASE_URL, API_BASE_URL
    ├── context/mi_perfil.md     # Perfil generado desde perfil_maestro.json
    ├── data/perfil_maestro.json # Fuente de verdad del perfil (sincronizada con BD)
    ├── outputs/                 # .tex y .pdf por usuario
    └── src/
        ├── api.py               # FastAPI — endpoints REST, CV, perfil, scrape
        ├── bot.py               # Telegram — /menu con InlineKeyboardMarkup
        ├── browser_agent.py     # Playwright scraper — términos derivados del perfil (lazy)
        ├── gemini_engine.py     # Groq LLM — CV LaTeX, compatibilidad rápida (caché perfil)
        ├── mcp_server.py        # 6 tools MCP: get/list/update/reset/save_cv/save_cl
        └── watcher.py           # DeepHealthWatcher — sync de estados cada 20 s
```

## Arranque (Docker)

```powershell
# Levantar todos los servicios (API + PostgreSQL)
docker compose up -d

# Frontend (terminal separada)
cd frontend; npm run dev
```

## Variables de entorno (`job_hunter/.env`)

| Variable | Descripción |
|---|---|
| `GROQ_API_KEY` | Key de console.groq.com |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/jobhunter` |
| `API_BASE_URL` | `http://127.0.0.1:8000` (default) |
| `BOT_MASTER_TOKEN` | Token del bot Telegram |

## Búsqueda autónoma — comportamiento

`browser_agent.py` genera los términos de búsqueda **de forma lazy** (solo si no se pasan `--terms`):
1. La API llama `generar_terminos_busqueda()` y pasa los términos vía `--terms` al subprocess.
2. El subprocess NO conecta a la BD en el arranque; los términos ya vienen listos.
3. Si se lanza manualmente sin `--terms`, entonces sí deriva los términos del `perfil_maestro.json`.

Términos generados para el perfil actual (Jair Molina):
- **SW**: Desarrollador Full Stack, Full Stack Developer, Desarrollador Python, Desarrollador React
- **IoT**: Desarrollador IoT, Ingeniero Sistemas Embebidos, Automatización Industrial, Desarrollador Firmware IoT
- **Mecánica**: Ingeniero Mecánico, Ingeniero Mecatrónico, Ingeniero CAD CAE, Ingeniero Control Automático

Plataformas: Computrabajo, OCC, Indeed (RSS), Bumeran, GetOnBrd (API), Remotive (API), LinkedIn.

## Evaluación de compatibilidad — eficiencia de tokens

`evaluar_compatibilidad_rapida()` usa un perfil compacto (título + 30 skills, ~150 chars) en lugar del perfil completo, y trunca requerimientos a 1200 chars. El perfil se cachea en memoria por proceso → 0 lecturas de disco tras la primera llamada.

## Generación de CV — paso a paso

1. Vacante en **No_Creado** → click **"Generar CV"** en el dashboard.
2. `POST /generar_cv/{id}` → Groq genera LaTeX → pdflatex compila.
3. Estado → `Revisado_IA`, aparecen botones **Ver PDF** y **Editar LaTeX**.
4. Para edición avanzada: copiar Prompt MCP → Claude Desktop → `save_latex_cv`.

## Bot de Telegram

| Botón | Acción |
|---|---|
| 🔍 Buscar Vacantes | Lanza `browser_agent --limit 3` en background |
| 📋 Ver Pendientes | Lista vacantes `No_Creado` / `Requiere_Correccion` |
| ⚙️ Resumen | Stats de la BD (total, por status, compatibilidad) |
| 🚀 Generar | `gen_{id}` → `generar_y_compilar` + Inspector IA |
| 📄 Descargar PDF | `pdf_{id}` → envía `outputs/cv_vacante_{id}.pdf` |
| ✅ Marcar Listo | `listo_{id}` → PATCH status → `Listo_Manual` |

## Regla de contexto

Leer `docs/` y `job_hunter/data/perfil_maestro.json` antes de proponer cambios al sistema.
