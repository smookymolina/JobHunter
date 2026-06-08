# AUDITORÍA DE MEJORAS — Job Hunter
> Estado actual: v1.1.5 · Fecha auditoría: 2026-06-05
> Modelo de negocio: el desarrollador no paga nada extra; el cliente desbloquea funciones premium.

---

## RESUMEN EJECUTIVO

Job Hunter es un sistema local de automatización de búsqueda de empleo con un pipeline bien definido:
`Scraping → SQLite → Kanban → IA (MCP/Claude) → LaTeX → PDF`

La app funciona end-to-end pero tiene fricción en puntos clave que frenan la autonomía total.
Este documento clasifica cada mejora en: **Free** (incluida en la app base) o **Pro** (desbloqueable por el usuario final).

---

## ESTADO ACTUAL DEL PIPELINE

```
[Perfil maestro JSON]
        ↓
[Scraper Playwright] → Computrabajo / OCC / LinkedIn (pendiente)
        ↓
[SQLite vacantes.db] ← blacklist de eliminadas
        ↓
[Dashboard Kanban] → polling 2 s
        ↓
[MCP Claude Desktop] → human-in-the-loop (cuello de botella)
        ↓
[LaTeX → pdflatex → PDF]
        ↓
[Listo_Manual] → fecha_postulacion registrada
```

**Cuello de botella principal**: el paso MCP es manual (usuario copia prompt → pega en Claude Desktop → espera). 
Romper este cuello de botella es la mejora más impactante y debe ser la función Pro central.

---

## CATEGORÍA 1 — GENERACIÓN DE CV AUTÓNOMA (impacto crítico)

### 1.1 Generación one-click desde el Dashboard (COMPLETADO ✅)

**Solución**: Botón "Generar CV" directamente en la VacanteCard que llama a `POST /generar_cv/{id}`.

**Implementación**:
- Frontend: `VacanteCard` llama a `api.generarCv(id)`.
- Backend: `api.py` usa `gemini_engine.py` (Groq) para generar LaTeX y compilar PDF.
- UI: El estado cambia a `En_Proceso` y luego a `Revisado_IA` automáticamente.

---

### 1.2 Generación batch (múltiples vacantes en cola) (PENDIENTE ⏳)

**Problema**: con 20 vacantes nuevas, el usuario genera una por una.

**Solución**: "Generar todo" en el header del Dashboard — pone en cola todas las vacantes en `No_Creado` con compatibilidad Alta/Media y las procesa secuencialmente con delay entre llamadas.

**Implementación**:
```python
# backend: POST /generar_cv/batch
async def generar_batch(ids: list[int], background_tasks: BackgroundTasks):
    for id in ids:
        background_tasks.add_task(generar_y_compilar, id)
    return {"ok": True, "queued": len(ids)}
```
```tsx
// frontend: botón "Generar todo" en Dashboard header
// filtra vacantes No_Creado con compatibilidad Alta o Media
// llama POST /generar_cv/batch con los IDs
// muestra progress: "Generando 3/7..."
```

**Tier**: PRO — límite free = 1 generación manual; Pro = cola ilimitada + batch automático.

---

### 1.3 Scheduler de generación automática nocturna

**Problema**: el usuario tiene que lanzar el scraper y la generación manualmente.

**Solución**: cron interno en el backend que cada N horas hace scrape + genera CVs automáticamente.

**Implementación**:
```python
# backend: APScheduler (pip install apscheduler)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=8, minute=0)  # 8am diario
async def rutina_diaria():
    # 1. scrape 10 nuevas vacantes
    await browser_agent_run(limit=10)
    # 2. generar CVs para Alta/Media compatibilidad
    pendientes = get_vacantes_no_creadas(compatibilidad=['Alta', 'Media'])
    for v in pendientes:
        await generar_y_compilar(v['id'])
```

```tsx
// frontend: sección "Automatización" en Perfil & Settings
// toggle: "Generación automática diaria" (ON/OFF)
// campo: hora de ejecución (default 08:00)
// muestra: "Última ejecución: hoy 08:01 — 3 CVs generados"
```

**Tier**: PRO — la automatización completa (sin intervención humana) es la función premium central.

---

## CATEGORÍA 2 — SCRAPING (impacto alto)

### 2.1 Soporte multi-portal

**Problema actual**: scraper solo en Computrabajo y OCC. LinkedIn, Indeed, Glassdoor, Bumeran no están cubiertos.

**Portales a agregar por prioridad**:
| Portal | Dificultad | Impacto |
|--------|-----------|---------|
| LinkedIn Jobs | Alta (anti-bot) | Muy alto |
| Indeed MX | Media | Alto |
| Glassdoor | Alta | Medio |
| Bumeran | Baja | Medio |
| El Economista Empleos | Baja | Bajo |

**Implementación** (patrón ya existente en `browser_agent.py`):
```python
# Cada portal es una función separada
async def scrape_indeed(page, term, limit):
    await page.goto(f"https://mx.indeed.com/jobs?q={term}&l=Mexico")
    # extraer títulos, empresas, enlaces, reqs
    ...

# Registro de scrapers
SCRAPERS = {
    'computrabajo': scrape_computrabajo,
    'occ': scrape_occ,
    'indeed': scrape_indeed,  # nuevo
    'bumeran': scrape_bumeran,  # nuevo
}

# POST /scrape acepta parámetro "portales": ["computrabajo", "occ", "indeed"]
```

```tsx
// frontend AddVacanteModal → tab Búsqueda autónoma
// checkboxes de portales (OCC ✓, Computrabajo ✓, Indeed □, Bumeran □)
// portales base: FREE; portales extra: PRO
```

**Tier**: FREE = OCC + Computrabajo; PRO = LinkedIn + Indeed + Glassdoor.

---

### 2.2 Filtros avanzados de scraping

**Problema**: el scraper trae vacantes de cualquier nivel/modalidad/salario.

**Solución**: filtros configurables desde la UI.

**Implementación**:
```python
# backend: ampliar FiltrosBusqueda en api.py
class FiltrosBusqueda(BaseModel):
    modalidad: list[str] = ['remoto', 'híbrido', 'presencial']
    nivel: list[str] = ['junior', 'semi-senior', 'senior']
    salario_min: int | None = None
    salario_max: int | None = None
    solo_recientes: bool = True  # < 7 días
    excluir_palabras: list[str] = []  # e.g. ["call center", "ventas"]
```

```tsx
// frontend: modal de configuración de filtros en Búsqueda autónoma
// salvo en localStorage/perfil_maestro.json como preferencias
```

**Tier**: FREE = filtros básicos (modalidad); PRO = salario mínimo + excluir palabras + solo recientes.

---

### 2.3 Deduplicación inteligente por similitud

**Problema**: distintos portales publican la misma vacante con títulos ligeramente distintos.
La blacklist actual solo chequea enlace exacto — no detecta duplicados semánticos.

**Solución**: al insertar, comparar título+empresa con hash fuzzy. Si similitud > 85% con existente, ignorar.

**Implementación**:
```python
# pip install rapidfuzz
from rapidfuzz import fuzz

def es_duplicado(titulo: str, empresa: str, existentes: list) -> bool:
    key = f"{titulo.lower()} {(empresa or '').lower()}"
    for e in existentes:
        ratio = fuzz.ratio(key, f"{e['titulo'].lower()} {(e['empresa'] or '').lower()}")
        if ratio > 85:
            return True
    return False
```

**Tier**: FREE — mejora la calidad de datos base.

---

## CATEGORÍA 3 — EVALUACIÓN DE COMPATIBILIDAD (impacto alto)

### 3.1 Evaluación detallada con score numérico

**Problema actual**: compatibilidad es Alta/Media/Baja/Nula — sin justificación ni score detallado.
`evaluar_compatibilidad_rapida` usa max 10 tokens (respuesta binaria).

**Solución**: segunda evaluación más profunda con breakdown por área.

**Implementación**:
```python
# gemini_engine.py — nueva función
async def evaluar_compatibilidad_detallada(vacante: dict, perfil: dict) -> dict:
    prompt = f"""
    Evalúa la compatibilidad del candidato con esta vacante.
    Responde SOLO JSON:
    {{
      "score": 0-100,
      "nivel": "Alta|Media|Baja|Nula",
      "fortalezas": ["..."],
      "brechas": ["..."],
      "recomendacion": "..."
    }}
    Vacante: {vacante['titulo']} - {vacante['requerimientos'][:500]}
    Perfil: {perfil['titulo_profesional']} - Skills: {perfil['habilidades']}
    """
    # Groq llama3-70b-8192 para análisis más profundo
```

```tsx
// frontend VacanteCard: expandir la sección de compatibilidad
// mostrar score numérico (ej. 78/100) + barras por área
// "Fortalezas: Python, React" / "Brechas: AWS, Docker"
```

**Tier**: FREE = nivel actual (Alta/Media/Baja); PRO = score numérico + breakdown detallado.

---
### 3.2 Ranking automático de vacantes (COMPLETADO ✅)

**Solución**: Ordenar Kanban por favorito y score de compatibilidad descendente.

**Implementación**: `KanbanBoard.tsx` implementa `sortColumn` usando un mapa de pesos para Alta, Media, Baja y Nula.

---

### 6.2 Búsqueda y filtros en el Kanban (PENDIENTE ⏳)
## CATEGORÍA 4 — GESTIÓN DE CV (impacto alto)

### 4.1 Historial de versiones de CV por vacante

**Problema**: si el usuario edita el LaTeX y recompila, la versión anterior se pierde.

**Solución**: guardar historial de versiones en `outputs/cv_vacante_{id}_v{n}.tex`.

**Implementación**:
```python
# api.py — POST /latex/{id}
def save_latex(id, content):
    # antes de sobrescribir, versionar
    current = f"outputs/cv_vacante_{id}.tex"
    if os.path.exists(current):
        versions = glob(f"outputs/cv_vacante_{id}_v*.tex")
        n = len(versions) + 1
        shutil.copy(current, f"outputs/cv_vacante_{id}_v{n}.tex")
    # guardar nueva versión
    write(current, content)
    compilar_pdf(id)
```

```tsx
// frontend: en modal editor LaTeX mostrar dropdown "Versiones anteriores"
// click → carga esa versión en el editor
```

**Tier**: FREE = guardar historial; PRO = comparar diff entre versiones.

---

### 4.2 Export masivo de PDFs

**Problema**: no hay forma de descargar todos los CVs generados de una vez.

**Solución**: botón "Exportar todo" que genera un ZIP con los PDFs de todas las vacantes en Revisado_IA/Listo_Manual.

**Implementación**:
```python
# backend: GET /export/pdfs
import zipfile

@app.get("/export/pdfs")
def export_pdfs(status: str = "Revisado_IA"):
    vacantes = get_vacantes_by_status(status)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for v in vacantes:
            pdf = f"outputs/cv_vacante_{v['id']}.pdf"
            if os.path.exists(pdf):
                zf.write(pdf, f"CV_{v['empresa']}_{v['titulo'][:30]}.pdf")
    buf.seek(0)
    return StreamingResponse(buf, media_type='application/zip',
        headers={"Content-Disposition": "attachment; filename=CVs_JobHunter.zip"})
```

**Tier**: PRO — diferenciador de valor para usuarios con muchas aplicaciones activas.

---

### 4.3 Previsualizador de PDF integrado mejorado

**Problema actual**: el modal de PDF usa `<iframe>` que en algunos navegadores/OS tiene restricciones CSP.

**Solución**: usar `react-pdf` (renderizado client-side) en lugar de iframe.

**Implementación**:
```bash
npm install react-pdf
```
```tsx
import { Document, Page } from 'react-pdf'

// reemplazar <iframe src={api.pdfUrl(id)} /> por:
<Document file={api.pdfUrl(id)}>
  <Page pageNumber={1} width={700} />
</Document>
```

**Tier**: FREE — mejora la experiencia base del editor.

---

## CATEGORÍA 5 — ANALÍTICA Y SEGUIMIENTO (impacto medio-alto)

### 5.1 Panel de métricas de búsqueda

**Problema**: no hay visibilidad de la efectividad de la búsqueda. ¿Cuántos CVs enviados? ¿Cuántas respuestas?

**Solución**: nueva sección "Analytics" en el Dashboard con métricas clave.

**Métricas a mostrar**:
- Total vacantes scrapeadas / semana
- Tasa de compatibilidad (% Alta vs Baja)
- CVs generados vs enviados
- Tiempo promedio No_Creado → Listo_Manual
- Portales con más vacantes compatibles

**Implementación**:
```python
# backend: GET /analytics
@app.get("/analytics")
def analytics():
    with sqlite3.connect(DB_PATH) as con:
        stats = {
            "total": con.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0],
            "por_status": dict(con.execute(
                "SELECT status, COUNT(*) FROM vacantes GROUP BY status").fetchall()),
            "por_compatibilidad": dict(con.execute(
                "SELECT compatibilidad, COUNT(*) FROM vacantes GROUP BY compatibilidad").fetchall()),
            "enviados_7d": con.execute(
                "SELECT COUNT(*) FROM vacantes WHERE fecha_postulacion >= datetime('now','-7 days')").fetchone()[0],
        }
    return stats
```

```tsx
// frontend: cards de métricas en Dashboard (sobre el Kanban)
// mini gráfico de barras con recharts (npm install recharts)
// "Esta semana: 15 scrapeadas · 8 CVs generados · 3 enviados"
```

**Tier**: FREE = métricas básicas (contadores); PRO = gráficas históricas + exportar reporte.

---

### 5.2 Seguimiento post-postulación (CRM básico)

**Problema**: una vez marcada como Listo_Manual, la vacante desaparece del flujo. No hay seguimiento.

**Solución**: estado adicional `En_Seguimiento` y recordatorios.

**Nuevos estados**:
```
Listo_Manual → En_Seguimiento → Entrevista_1 → Entrevista_2 → Oferta | Rechazado
```

**Implementación**:
```python
# backend: ampliar CHECK de status en SQLite migration
ALTER TABLE vacantes ADD COLUMN notas TEXT;  -- notas de seguimiento
# nuevos estados: En_Seguimiento, Entrevista_1, Entrevista_2, Oferta, Rechazado
```

```tsx
// frontend: nueva columna "Seguimiento" en Kanban (colapsable)
// VacanteCard en seguimiento: campo de notas + cambio de estado
// recordatorio: "Hace 7 días sin respuesta — ¿hacer follow-up?"
```

**Tier**: PRO — el CRM post-postulación es un diferenciador claro de la versión premium.

---

### 5.3 Recordatorios via Telegram

**Problema**: el bot solo actúa cuando el usuario lo invoca. No hay notificaciones push.

**Solución**: el bot envía mensajes proactivos en situaciones clave.

**Eventos a notificar**:
- Scrape completado: "Se encontraron 8 vacantes nuevas (3 con compatibilidad Alta)"
- CV generado: "CV listo para Empresa X — ¿enviar?"
- Follow-up: "Han pasado 7 días desde tu postulación a Empresa Y — ¿hacer seguimiento?"
- Error: "pdflatex falló para vacante #14 — requiere corrección"

**Implementación**:
```python
# bot.py — función de notificación reutilizable
async def notify(message: str):
    """Envía mensaje al CHAT_ID configurado en .env"""
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if chat_id:
        await application.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')

# Llamar desde api.py después de eventos clave:
await notify(f"✅ CV generado para <b>{vacante['empresa']}</b> — /detalles {id}")
await notify(f"🔍 Scrape completado: {n} vacantes nuevas ({alta} Alta compatibilidad)")
```

**Tier**: FREE = notificaciones básicas (scrape + CV listo); PRO = follow-up automático + recordatorios CRM.

---

## CATEGORÍA 6 — UX Y FRONTEND (impacto medio)

### 6.1 Modo offline / sync status indicator

**Problema**: cuando el backend cae, el frontend muestra errores poco descriptivos.

**Solución**: indicador de estado de conexión persistente + modo degradado con datos cacheados.

**Implementación**:
```tsx
// hook useApiStatus — monitorea /debug/sync-health cada 5s
// cuando cae: banner "API desconectada — mostrando últimos datos conocidos"
// cachear última respuesta en localStorage por sección
```

**Tier**: FREE — mejora la robustez de la UX base.

---

### 6.2 Búsqueda y filtros en el Kanban

**Problema**: con 50+ vacantes, el Kanban se vuelve difícil de navegar.

**Solución**: barra de búsqueda + filtros rápidos encima del Kanban.

**Filtros rápidos**:
- Por compatibilidad (Alta / Media / Baja)
- Por empresa (dropdown)
- Por fecha (Hoy / Esta semana / Este mes)
- Mostrar solo con errores (Requiere_Correccion)

**Implementación**:
```tsx
// frontend Dashboard: search bar + filter pills encima del KanbanBoard
// filtro se aplica en memoria (no requiere backend)
// estado de filtros en URL params para compartir/bookmarkear
```

**Tier**: FREE — no requiere backend.

---

### 6.3 Vista lista vs Kanban toggle

**Problema**: el Kanban es excelente para pocos registros pero con 100+ vacantes es lento visualmente.

**Solución**: toggle entre vista Kanban y vista tabla (como Mis Vacantes pero más rica).

**Tier**: FREE — alternar entre dos vistas ya existentes.

---

### 6.4 Onboarding guiado primer uso

**Problema**: un usuario nuevo no sabe por dónde empezar. No hay guía de primeros pasos.

**Solución**: wizard de 3 pasos al primer arranque.

```
Paso 1: Completa tu perfil (redirect a /perfil)
Paso 2: Lanza tu primera búsqueda (botón scrape)
Paso 3: Genera tu primer CV (tutorial MCP o one-click si Pro)
```

**Implementación**:
```tsx
// localStorage: 'onboarding_done' = false por defecto
// si false: overlay semi-transparente con steps
// cada step se marca done al completar la acción
```

**Tier**: FREE — onboarding básico mejora la activación de usuarios.

---

## CATEGORÍA 7 — BACKEND / INFRAESTRUCTURA (impacto técnico)

### 7.1 Rate limiting en el scraper

**Problema**: el scraper puede ser bloqueado por IP si hace demasiadas requests.

**Solución**: delays aleatorios + rotación de User-Agent + manejo de CAPTCHA.

**Implementación**:
```python
# browser_agent.py
import random

async def scrape_portal(page, term, limit, portal):
    # delay humano entre páginas
    await asyncio.sleep(random.uniform(2.0, 5.0))
    
    # rotar user-agent
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...",
    ]
    await page.set_extra_http_headers({"User-Agent": random.choice(agents)})
    
    # detección de CAPTCHA — pausar y notificar
    if await page.locator('[id*="captcha"]').count() > 0:
        await notify("⚠️ CAPTCHA detectado en scraping — pausando 30 min")
        await asyncio.sleep(1800)
```

**Tier**: FREE — seguridad operativa base.

---

### 7.2 Caché de compatibilidad

**Problema**: `evaluar_compatibilidad_rapida` llama a Groq por cada vacante. Con 50 vacantes = 50 llamadas API.

**Solución**: cachear el resultado por hash(vacante.requerimientos + perfil.skills). Si el perfil no cambió y los reqs son iguales, usar cache.

**Implementación**:
```python
import hashlib
_cache: dict[str, str] = {}

def evaluar_con_cache(reqs: str, perfil_hash: str) -> str:
    key = hashlib.md5(f"{reqs[:300]}{perfil_hash}".encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    result = evaluar_compatibilidad_rapida(reqs, perfil)
    _cache[key] = result
    return result
```

**Tier**: FREE — ahorra costos de API y acelera el scraping.

---

### 7.3 Múltiples perfiles / CV por persona

**Problema**: el sistema asume un solo usuario. Si la persona quiere postular con perfiles distintos (ej. perfil técnico vs perfil gerencial), no puede.

**Solución**: soporte de múltiples perfiles en `perfil_maestro.json` con switch activo.

**Implementación**:
```python
# backend: GET /api/perfiles → lista de perfiles
# POST /api/perfiles/{nombre} → crea/actualiza perfil
# PATCH /api/perfil/activo → cambia perfil activo
```

```tsx
// frontend: Perfil & Settings → dropdown "Perfil activo: Técnico ▼"
// botón "Nuevo perfil" → duplica el actual con nuevo nombre
```

**Tier**: PRO — múltiples perfiles es una función de poder para usuarios avanzados.

---

### 7.4 API Key propia del usuario (bring-your-own-key)

**Problema actual**: la app usa `GROQ_API_KEY` hardcodeada en `.env`. Si el usuario no tiene Groq, la app no funciona.

**Solución**: permitir que el usuario ingrese su propia API key desde la UI de Perfil & Settings.

**Providers soportados**:
- Groq (gratuito, actual) — para evaluación de compatibilidad
- OpenAI — para generación de CV (alternativa a MCP)
- Anthropic — para generación de CV one-click desde la app

**Implementación**:
```tsx
// frontend Perfil & Settings → sección "API Keys"
// inputs: GROQ_API_KEY, ANTHROPIC_API_KEY (opcional)
// guardado encriptado en localStorage con AES-256
// botón "Probar conexión" → GET /api/test-key?provider=groq
```

```python
# backend: recibir key por header X-API-Key en lugar de solo .env
# fallback: si no hay key en header, usar .env
```

**Tier**: FREE = Groq key propia; PRO = Anthropic/OpenAI key + generación one-click.

---

## CATEGORÍA 8 — MODELO FREEMIUM (monetización)

### Tabla de features Free vs Pro

| Feature | Free | Pro |
|---------|------|-----|
| Scraping OCC + Computrabajo | ✅ | ✅ |
| Scraping LinkedIn + Indeed | ❌ | ✅ |
| Kanban básico | ✅ | ✅ |
| Generación CV via MCP (manual) | ✅ | ✅ |
| Generación CV one-click | ❌ | ✅ |
| Generación batch automática | ❌ | ✅ |
| Scheduler nocturno | ❌ | ✅ |
| Compatibilidad Alta/Media/Baja | ✅ | ✅ |
| Score numérico + breakdown | ❌ | ✅ |
| Historial de versiones CV | ✅ | ✅ |
| Export ZIP de PDFs | ❌ | ✅ |
| Métricas básicas (contadores) | ✅ | ✅ |
| Gráficas históricas + reportes | ❌ | ✅ |
| CRM post-postulación | ❌ | ✅ |
| Notificaciones Telegram básicas | ✅ | ✅ |
| Follow-up automático | ❌ | ✅ |
| Múltiples perfiles | ❌ | ✅ |
| Filtros avanzados de scraping | Básicos | Avanzados |
| API Key propia (Groq) | ✅ | ✅ |
| API Key Anthropic/OpenAI | ❌ | ✅ |

### Cómo implementar el gate freemium

**Opción A — Feature flags locales (más simple)**:
```json
// job_hunter/data/license.json (encriptado)
{
  "tier": "free",       // o "pro"
  "key": "...",         // hash de licencia
  "expires": null       // null = vitalicia
}
```

```python
# backend: middleware de licencia
def check_pro(feature: str):
    lic = load_license()
    if lic['tier'] == 'free' and feature in PRO_FEATURES:
        raise HTTPException(status_code=402, detail=f"Feature '{feature}' requiere Pro")
```

```tsx
// frontend: hook useLicense()
// si feature no disponible: botón "Desbloquear Pro" en lugar de la acción
// modal de pago simple (Gumroad / Stripe Payment Link / MercadoPago)
```

**Opción B — Servidor de activación remoto (más segura)**:
```
Usuario compra en Gumroad → recibe key única → la ingresa en Settings
App llama GET https://api.jobhunter.dev/activate?key=XXX → valida y devuelve token JWT
Token se guarda localmente, expira según tier (mensual/anual/vitalicio)
```

### Precio sugerido

| Tier | Precio | Modelo |
|------|--------|--------|
| Free | $0 | Siempre gratis, funciones base |
| Pro Monthly | $9.99 USD/mes | Renovación automática |
| Pro Annual | $79 USD/año | 33% descuento vs mensual |
| Pro Lifetime | $149 USD | Pago único, todas las actualizaciones |

**Canal de venta recomendado**: Gumroad (sin setup fee, 10% comisión solo si vende).
- No requiere infraestructura de servidor propia
- Manejo automático de pagos internacionales
- Sistema de licencias built-in

---

## PRIORIDAD DE IMPLEMENTACIÓN

### Sprint 1 — Quick wins (1-2 días c/u, impacto inmediato)
1. **Botón "Generar CV" one-click** (cat 1.1) — conectar botón a `POST /generar_cv/{id}`
2. **Ordenar Kanban por compatibilidad** (cat 3.2) — solo frontend
3. **Filtros en Kanban** (cat 6.2) — solo frontend
4. **Notificaciones Telegram de scrape** (cat 5.3) — 20 líneas en bot.py

### Sprint 2 — Core value (3-5 días c/u)
5. **Score de compatibilidad detallado** (cat 3.1) — backend + UI
6. **Panel de métricas** (cat 5.1) — backend + recharts
7. **Generación batch** (cat 1.2) — backend endpoint + frontend
8. **Deduplicación fuzzy** (cat 2.3) — backend puro

### Sprint 3 — Premium features (1 semana c/u)
9. **Scheduler automático nocturno** (cat 1.3) — APScheduler + UI settings
10. **CRM post-postulación** (cat 5.2) — DB schema + UI nueva columna
11. **Múltiples perfiles** (cat 7.3) — backend + UI
12. **Export ZIP PDFs** (cat 4.2) — backend puro

### Sprint 4 — Monetización (2 semanas)
13. **Sistema de licencias** (cat 8) — feature flags + UI upgrade
14. **Portales adicionales** (cat 2.1) — Indeed + Bumeran scrapers

---

## BUGS Y DEUDA TÉCNICA IDENTIFICADOS

| # | Descripción | Severidad | Archivo |
|---|-------------|-----------|---------|
| B1 | `refresh` en PlantillasPage redefinido dos veces tras el refactor | Media | `plantillas/page.tsx` |
| B2 | `AvatarContext.setInitials` en dependency array de useEffect puede causar re-renders | Baja | `perfil/page.tsx` |
| B3 | `api.uploadTemplate` usa `form.append('file', ...)` pero campo no está validado en backend que el nombre sea exactamente `file` | Baja | `api.ts` + `api.py` |
| B4 | `watcher.py` no maneja el caso de vacante eliminada mientras el watcher corre (KeyError potencial) | Media | `watcher.py` |
| B5 | El scraper no tiene timeout por portal — si un portal cuelga, bloquea todo el proceso | Alta | `browser_agent.py` |
| B6 | `evaluar_compatibilidad_rapida` no tiene retry en caso de fallo de red con Groq | Media | `gemini_engine.py` |
| B7 | Los PDFs se sirven sin caché HTTP (`Cache-Control`) — cada "Ver PDF" descarga el archivo completo | Baja | `api.py GET /pdf/{id}` |

---

## ARQUITECTURA FUTURA (visión 6 meses)

```
[Job Hunter Local v2.0]
        │
        ├── Core (Free, local)
        │   ├── Scraper multi-portal (OCC, Computrabajo, Bumeran, Indeed)
        │   ├── Evaluación de compatibilidad básica
        │   ├── Generación CV via MCP (human-in-the-loop)
        │   ├── Kanban + filtros + búsqueda
        │   └── Bot Telegram (notificaciones básicas)
        │
        ├── Pro (local, desbloqueado con licencia)
        │   ├── Generación CV one-click (Groq/Anthropic)
        │   ├── Scheduler automático nocturno
        │   ├── Score de compatibilidad numérico
        │   ├── CRM post-postulación
        │   ├── Múltiples perfiles
        │   ├── Export PDF masivo
        │   └── Scrapers LinkedIn + Glassdoor
        │
        └── Cloud (SaaS futuro — v3.0)
            ├── Multi-usuario
            ├── Scraping en servidores propios (sin Playwright local)
            ├── Dashboard web público (sin instalar nada)
            └── Integración directa con portales via API oficial
```

---

*Auditoría generada con visión completa del código fuente v1.1.5 · 2026-06-05*
*Actualizar este documento con cada sprint completado.*
