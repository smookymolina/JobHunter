import sys
sys.stdout.reconfigure(encoding='utf-8')

import io
import json
import os
import re
import asyncio
import threading
import time
import urllib.error
import urllib.request
import logging
from functools import wraps

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

# ── Config ────────────────────────────────────────────────────────────────────

TOKEN         = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID      = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))
API_BASE      = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
OUTPUTS_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs'))
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'latex_templates'))
CONF_FILE     = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot_conf.json'))
PAGE_SIZE     = 5

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger("bot")

# ── Conf persistence ──────────────────────────────────────────────────────────

def load_conf() -> dict:
    try:
        with open(CONF_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"auto_scrape": False, "debug_mode": False}

def save_conf(data: dict) -> None:
    try:
        with open(CONF_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        log.warning("No se pudo guardar conf: %s", e)

# ── Security ──────────────────────────────────────────────────────────────────

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *a, **kw):
        uid = update.effective_user.id if update.effective_user else 0
        if ADMIN_ID and uid != ADMIN_ID:
            if update.callback_query:
                await update.callback_query.answer("⛔ Acceso no autorizado.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Acceso no autorizado.")
            return
        return await func(update, ctx, *a, **kw)
    return wrapper

# ── API helpers ───────────────────────────────────────────────────────────────

def _api_sync(method: str, path: str, data=None, raw_body: bytes | None = None,
              content_type: str = "application/json"):
    url = f"{API_BASE}{path}"
    if data is not None:
        body = json.dumps(data).encode()
        ct   = "application/json"
    elif raw_body is not None:
        body = raw_body
        ct   = content_type
    else:
        body = None
        ct   = content_type
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": ct} if body else {},
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 409:
            log.debug("Saltando duplicado en %s %s", method, path)
            return json.loads(e.read().decode("utf-8", errors="replace") or "{}")
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail[:300]}")
    except Exception as e:
        raise RuntimeError(f"Error de conexión con la API: {e}")

async def api(method: str, path: str, data=None,
              raw_body: bytes | None = None, content_type: str = "application/json"):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: _api_sync(method, path, data, raw_body, content_type)
    )

def _heartbeat_loop() -> None:
    while True:
        try:
            req = urllib.request.Request(
                f"{API_BASE}/bot/heartbeat", data=b"", method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass
        time.sleep(30)

def start_heartbeat() -> None:
    t = threading.Thread(target=_heartbeat_loop, daemon=True, name="bot-heartbeat")
    t.start()

def heartbeat_api() -> None:
    try:
        req = urllib.request.Request(f"{API_BASE}/vacantes?limit=1", method="GET")
        with urllib.request.urlopen(req, timeout=5) as r:
            payload = json.loads(r.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise RuntimeError("Respuesta inesperada del endpoint /vacantes")
        log.info("Conexión con API establecida: OK")
        print("Conexión con API establecida: OK")
    except Exception as e:
        log.critical("Fallo crítico en el heartbeat con la API: %s", e)
        raise SystemExit(f"Fallo crítico: no se pudo conectar con la API en {API_BASE}.")

# ── Helpers ───────────────────────────────────────────────────────────────────

STATUS_ICON = {
    "No_Creado": "⬜", "En_Proceso": "🔵",
    "Revisado_IA": "🟡", "Listo_Manual": "🟢", "Requiere_Correccion": "🔴",
}
COMPAT_ICON = {"Alta": "🔥", "Media": "🟠", "Baja": "🔵", "Nula": "⚪"}

def fmt_st(s: str) -> str:
    return f"{STATUS_ICON.get(s,'❓')} {s}"

def fmt_co(c: str) -> str:
    return f"{COMPAT_ICON.get(c,'❓')} {c}"

def esc(t: str) -> str:
    return (t or "").replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")

def pdf_path(vid: int) -> str:
    return os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.pdf")

def tex_path(vid: int) -> str:
    return os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.tex")

def has_pdf(vid: int) -> bool:
    return os.path.exists(pdf_path(vid))

# ── Keyboard builders ─────────────────────────────────────────────────────────

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Buscar Vacantes",   callback_data="buscar")],
        [InlineKeyboardButton("📊 Dashboard",          callback_data="dashboard")],
        [InlineKeyboardButton("📋 Mis Vacantes",       callback_data="vacantes:0"),
         InlineKeyboardButton("📥 Mis CVs",            callback_data="cvs:0")],
        [InlineKeyboardButton("👤 Mi Perfil",          callback_data="perfil")],
        [InlineKeyboardButton("🤖 Acciones IA",        callback_data="ia")],
        [InlineKeyboardButton("⚙️ Configuración",      callback_data="conf")],
    ])

def kb_back(dest: str = "menu") -> InlineKeyboardMarkup:
    label = "◀️ Menú Principal" if dest == "menu" else "◀️ Volver"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_buscar() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("3 vacantes",  callback_data="buscar:3"),
         InlineKeyboardButton("5 vacantes",  callback_data="buscar:5")],
        [InlineKeyboardButton("10 vacantes", callback_data="buscar:10"),
         InlineKeyboardButton("20 vacantes", callback_data="buscar:20")],
        [InlineKeyboardButton("◀️ Volver",   callback_data="menu")],
    ])

def kb_vacantes(rows: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    btns = []
    for v in rows:
        icon  = COMPAT_ICON.get(v.get("compatibilidad", "Nula"), "❓")
        cv    = "📄" if has_pdf(v["id"]) else "  "
        label = f"{icon}{cv} #{v['id']} {v['titulo'][:26]}"
        btns.append([InlineKeyboardButton(label, callback_data=f"vac:{v['id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"vacantes:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"vacantes:{page+1}"))
    if nav:
        btns.append(nav)
    btns.append([InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")])
    return InlineKeyboardMarkup(btns)

def kb_vacante_detalle(vid: int, status: str, tiene_pdf: bool = False) -> InlineKeyboardMarkup:
    rows = []

    row1 = []
    if status in ("No_Creado", "Requiere_Correccion"):
        row1.append(InlineKeyboardButton("🚀 Generar CV",   callback_data=f"gen:{vid}"))
    elif status == "En_Proceso":
        row1.append(InlineKeyboardButton("⏳ Generando…",  callback_data=f"vac:{vid}"))
    if tiene_pdf:
        row1.append(InlineKeyboardButton("📄 Ver PDF",      callback_data=f"pdf:{vid}"))
    if status in ("Revisado_IA", "Listo_Manual"):
        row1.append(InlineKeyboardButton("📝 Editar LaTeX", callback_data=f"tex:{vid}"))
    if row1:
        rows.append(row1)

    row2 = []
    if status != "Listo_Manual":
        row2.append(InlineKeyboardButton("✅ Marcar Listo",  callback_data=f"listo:{vid}"))
    row2.append(InlineKeyboardButton("🗑️ Borrar",            callback_data=f"del:{vid}"))
    rows.append(row2)

    rows.append([InlineKeyboardButton("◀️ Mis Vacantes", callback_data="vacantes:0")])
    return InlineKeyboardMarkup(rows)

def kb_cvs(items: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    btns = []
    for vid, titulo, status in items:
        icon  = STATUS_ICON.get(status, "❓")
        label = f"📄 {icon} #{vid} {titulo[:28]}"
        btns.append([InlineKeyboardButton(label, callback_data=f"pdf:{vid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"cvs:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"cvs:{page+1}"))
    if nav:
        btns.append(nav)
    btns.append([InlineKeyboardButton("🗑️ Ver vacante", callback_data="vacantes:0"),
                 InlineKeyboardButton("◀️ Menú",        callback_data="menu")])
    return InlineKeyboardMarkup(btns)

def kb_ia() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Limpiar DB",          callback_data="ia:clean")],
        [InlineKeyboardButton("⚡ Generar pendientes",   callback_data="ia:genall")],
        [InlineKeyboardButton("📥 Descargar todos PDFs", callback_data="ia:dlall")],
        [InlineKeyboardButton("🔄 Dashboard",            callback_data="dashboard")],
        [InlineKeyboardButton("◀️ Volver",               callback_data="menu")],
    ])

def kb_conf(auto: bool, debug: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'✅' if auto else '🔲'} Scraping automático",
            callback_data="conf:autoscrape",
        )],
        [InlineKeyboardButton(
            f"{'✅' if debug else '🔲'} Modo debug",
            callback_data="conf:debug",
        )],
        [InlineKeyboardButton("◀️ Volver", callback_data="menu")],
    ])

# ── Command handlers ──────────────────────────────────────────────────────────

@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conf = load_conf()
    ctx.bot_data.setdefault("auto_scrape", conf.get("auto_scrape", False))
    ctx.bot_data.setdefault("debug_mode",  conf.get("debug_mode",  False))
    await update.message.reply_text(
        "🤖 *Job Hunter Bot*\n\nControl total de tu búsqueda de empleo.\nElige una opción del menú:",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )

@admin_only
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 *Menú Principal*",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )

@admin_only
async def cmd_cvs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 *Mis CVs* — cargando...",
        parse_mode="Markdown",
    )
    try:
        all_v = await api("GET", "/vacantes?limit=500")
    except RuntimeError as e:
        await update.message.reply_text(f"❌ Error: `{esc(str(e))}`", parse_mode="Markdown")
        return
    items = [
        (v["id"], v.get("titulo", "—"), v.get("status", "?"))
        for v in all_v if has_pdf(v["id"])
    ]
    if not items:
        await update.message.reply_text(
            "📥 No hay CVs generados todavía.\n\nUsa 📋 Mis Vacantes → 🚀 Generar CV.",
        )
        return
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    slc = items[:PAGE_SIZE]
    await update.message.reply_text(
        f"📥 *Mis CVs* — Página 1/{total_pages}  ({len(items)} CVs generados)",
        parse_mode="Markdown",
        reply_markup=kb_cvs(slc, 0, total_pages),
    )

# ── Callback dispatcher ───────────────────────────────────────────────────────

@admin_only
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data

    # ── Menú principal ─────────────────────────────────────────────────────────
    if data == "menu":
        await q.answer()
        await q.edit_message_text(
            "🏠 *Menú Principal*",
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )

    # ── Dashboard ──────────────────────────────────────────────────────────────
    elif data == "dashboard":
        await q.answer()
        await _cb_dashboard(q)

    # ── Mi Perfil ──────────────────────────────────────────────────────────────
    elif data == "perfil":
        await q.answer()
        await _cb_perfil(q)

    # ── Buscar (sub-menú + acción) ─────────────────────────────────────────────
    elif data == "buscar":
        await q.answer()
        await q.edit_message_text(
            "🔍 *Buscar Vacantes*\n\n¿Cuántas vacantes buscar?\nSe usarán los términos de tu perfil automáticamente.",
            parse_mode="Markdown",
            reply_markup=kb_buscar(),
        )

    elif data.startswith("buscar:"):
        cantidad = int(data.split(":")[1])
        await q.answer(f"Iniciando búsqueda de {cantidad} vacantes…")
        await _cb_buscar(q, cantidad)

    # ── Mis Vacantes ───────────────────────────────────────────────────────────
    elif data.startswith("vacantes:"):
        await q.answer()
        page = int(data.split(":")[1])
        await _cb_vacantes(q, page)

    elif data.startswith("vac:"):
        await q.answer()
        vid = int(data.split(":")[1])
        await _cb_vacante_detalle(q, vid)

    # ── Mis CVs ────────────────────────────────────────────────────────────────
    elif data.startswith("cvs:"):
        await q.answer()
        page = int(data.split(":")[1])
        await _cb_cvs(q, page)

    # ── Acciones sobre vacante ─────────────────────────────────────────────────
    elif data.startswith("gen:"):
        vid = int(data.split(":")[1])
        await q.answer(f"Generando CV #{vid}…")
        await _cb_generar(q, ctx, vid)

    elif data.startswith("pdf:"):
        vid = int(data.split(":")[1])
        await _cb_enviar_pdf(q, vid)

    elif data.startswith("tex:"):
        vid = int(data.split(":")[1])
        await q.answer("Cargando LaTeX…")
        await _cb_editar_latex(q, ctx, vid)

    elif data.startswith("listo:"):
        vid = int(data.split(":")[1])
        await _cb_marcar_listo(q, vid)

    elif data.startswith("del:"):
        vid = int(data.split(":")[1])
        await _cb_borrar(q, vid)

    # ── Acciones IA ────────────────────────────────────────────────────────────
    elif data == "ia":
        await q.answer()
        await q.edit_message_text(
            "🤖 *Acciones IA*\n\nOperaciones sobre el pipeline completo:",
            parse_mode="Markdown",
            reply_markup=kb_ia(),
        )

    elif data == "ia:clean":
        await q.answer()
        await _cb_clean_confirm(q)

    elif data == "ia:clean:ok":
        await q.answer("Limpiando…")
        await _cb_clean_exec(q)

    elif data == "ia:genall":
        await q.answer("Iniciando generación masiva…")
        await _cb_genall(q, ctx)

    elif data == "ia:dlall":
        await q.answer("Preparando descarga masiva…")
        await _cb_dlall(q)

    # ── Configuración ──────────────────────────────────────────────────────────
    elif data == "conf":
        await q.answer()
        await q.edit_message_text(
            "⚙️ *Configuración*",
            parse_mode="Markdown",
            reply_markup=kb_conf(
                ctx.bot_data.get("auto_scrape", False),
                ctx.bot_data.get("debug_mode",  False),
            ),
        )

    elif data == "conf:autoscrape":
        val = not ctx.bot_data.get("auto_scrape", False)
        ctx.bot_data["auto_scrape"] = val
        save_conf({"auto_scrape": val, "debug_mode": ctx.bot_data.get("debug_mode", False)})
        await q.answer("Activado ✅" if val else "Desactivado 🔲")
        await q.edit_message_text(
            f"⚙️ *Configuración*\n\nScraping automático: {'✅ Activado' if val else '🔲 Desactivado'}",
            parse_mode="Markdown",
            reply_markup=kb_conf(val, ctx.bot_data.get("debug_mode", False)),
        )

    elif data == "conf:debug":
        val = not ctx.bot_data.get("debug_mode", False)
        ctx.bot_data["debug_mode"] = val
        save_conf({"auto_scrape": ctx.bot_data.get("auto_scrape", False), "debug_mode": val})
        await q.answer("Debug ON 🐛" if val else "Debug OFF")
        await q.edit_message_text(
            f"⚙️ *Configuración*\n\nModo debug: {'🐛 Activado' if val else '🔇 Desactivado'}",
            parse_mode="Markdown",
            reply_markup=kb_conf(ctx.bot_data.get("auto_scrape", False), val),
        )

    else:
        await q.answer("Acción desconocida.", show_alert=True)

# ── Dashboard ─────────────────────────────────────────────────────────────────

async def _cb_dashboard(q):
    try:
        vacantes = await api("GET", "/vacantes?limit=500")
        scrape   = await api("GET", "/scrape/status")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ *Error en servidor:* la API no responde.\n\n`{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    total  = len(vacantes)
    by_st  = {}
    by_co  = {}
    n_pdfs = 0
    for v in vacantes:
        s = v.get("status", "?");        by_st[s] = by_st.get(s, 0) + 1
        c = v.get("compatibilidad", "?"); by_co[c] = by_co.get(c, 0) + 1
        if has_pdf(v["id"]):
            n_pdfs += 1

    pendientes = by_st.get("No_Creado", 0) + by_st.get("Requiere_Correccion", 0)
    en_proceso = by_st.get("En_Proceso", 0)
    revisados  = by_st.get("Revisado_IA", 0)
    listos     = by_st.get("Listo_Manual", 0)

    scrape_txt = "🟢 Activo" if scrape.get("running") else "⚪ Inactivo"
    last       = scrape.get("last") or "—"

    lines_st = "\n".join(f"  {fmt_st(s)}: {c}" for s, c in sorted(by_st.items()))
    lines_co = "\n".join(f"  {fmt_co(k)}: {n}" for k, n in sorted(by_co.items()))

    text = (
        f"📊 *Dashboard — Job Hunter*\n\n"
        f"📁 Total vacantes: *{total}*\n"
        f"⏳ Pendientes: *{pendientes}*\n"
        f"🔵 En proceso: *{en_proceso}*\n"
        f"🟡 Revisados IA: *{revisados}*\n"
        f"🟢 Listos: *{listos}*\n"
        f"📄 PDFs generados: *{n_pdfs}*\n\n"
        f"🔍 Scraper: {scrape_txt}\n"
        f"   Último: _{esc(last[:80])}_\n\n"
        f"*Por status:*\n{lines_st}\n\n"
        f"*Por compatibilidad:*\n{lines_co}"
    )
    await q.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Actualizar",    callback_data="dashboard"),
             InlineKeyboardButton("📥 Mis CVs",       callback_data="cvs:0")],
            [InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")],
        ]),
    )

# ── Mi Perfil ─────────────────────────────────────────────────────────────────

async def _cb_perfil(q):
    try:
        perfil = await api("GET", "/api/perfil")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ *Perfil no disponible*\n\n`{esc(str(e))}`\n\n"
            "Sube tu perfil desde el dashboard web o configura `data/perfil_maestro.json`.",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    nombre    = esc(f"{perfil.get('nombre','')} {perfil.get('apellidos','')}".strip())
    titulo    = esc(perfil.get("titulo_profesional", "—"))
    email     = esc(perfil.get("email", "—"))
    telefono  = esc(perfil.get("telefono", "—"))
    ubicacion = esc(perfil.get("ubicacion", "—"))
    habs      = perfil.get("habilidades", {})
    n_skills  = sum(len(v) for v in habs.values() if isinstance(v, list))
    categorias = ", ".join(habs.keys()) or "—"

    text = (
        f"👤 *Mi Perfil*\n\n"
        f"*{nombre}*\n"
        f"_{titulo}_\n\n"
        f"📧 {email}\n"
        f"📱 {telefono}\n"
        f"📍 {ubicacion}\n\n"
        f"🛠 *{n_skills}* habilidades registradas\n"
        f"📂 Categorías: _{categorias}_"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb_back())

# ── Mis Vacantes ──────────────────────────────────────────────────────────────

async def _cb_vacantes(q, page: int):
    try:
        all_v = await api("GET", "/vacantes?limit=500")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ *Error cargando vacantes:*\n`{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    total = len(all_v)
    if total == 0:
        await q.edit_message_text(
            "📋 No hay vacantes registradas.\n\nUsa 🔍 Buscar Vacantes para empezar.",
            reply_markup=kb_back(),
        )
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    slc  = all_v[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    await q.edit_message_text(
        f"📋 *Mis Vacantes* — Página {page+1}/{total_pages}  ({total} total)\n"
        f"_(📄 = tiene PDF generado)_",
        parse_mode="Markdown",
        reply_markup=kb_vacantes(slc, page, total_pages),
    )

async def _cb_vacante_detalle(q, vid: int):
    try:
        v = await api("GET", f"/vacantes/{vid}")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ Vacante #{vid} no encontrada.\n`{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back("vacantes:0"),
        )
        return

    reqs = v.get("requerimientos") or "Sin datos"
    if len(reqs) > 600:
        reqs = reqs[:600] + "…"

    tiene = has_pdf(vid)
    pdf_indicator = " 📄 PDF listo" if tiene else ""

    text = (
        f"*\\#{v['id']} — {esc(v['titulo'][:50])}*\n"
        f"🏢 _{esc(v.get('empresa','—'))}_\n"
        f"📅 {(v.get('fecha_registro') or '')[:10]}{pdf_indicator}\n"
        f"🎯 {fmt_co(v.get('compatibilidad','Nula'))} | {fmt_st(v.get('status','?'))}\n"
        f"🔗 {esc(v.get('enlace','—'))}\n\n"
        f"📋 *Requerimientos:*\n{esc(reqs)}"
    )
    await q.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=kb_vacante_detalle(vid, v.get("status", "No_Creado"), tiene),
    )

# ── Mis CVs ───────────────────────────────────────────────────────────────────

async def _cb_cvs(q, page: int):
    try:
        all_v = await api("GET", "/vacantes?limit=500")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ Error: `{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    items = [
        (v["id"], v.get("titulo", "—"), v.get("status", "?"))
        for v in all_v if has_pdf(v["id"])
    ]

    if not items:
        await q.edit_message_text(
            "📥 *Mis CVs*\n\nNo hay CVs generados todavía.\n\n"
            "Usa 📋 *Mis Vacantes* → 🚀 *Generar CV* para crear el primero.",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    total       = len(items)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page        = max(0, min(page, total_pages - 1))
    slc         = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    await q.edit_message_text(
        f"📥 *Mis CVs* — Página {page+1}/{total_pages}  ({total} CVs generados)\n"
        f"_Toca un CV para descargarlo._",
        parse_mode="Markdown",
        reply_markup=kb_cvs(slc, page, total_pages),
    )

# ── Buscar vacantes ───────────────────────────────────────────────────────────

async def _cb_buscar(q, cantidad: int):
    await q.edit_message_text(
        f"🔍 Iniciando búsqueda de *{cantidad}* vacantes...\n"
        f"Se usarán los términos derivados de tu perfil.",
        parse_mode="Markdown",
    )
    try:
        result = await api("POST", "/scrape", {"cantidad": cantidad})
        msg    = esc(result.get("mensaje", "Scraping iniciado."))
        terms  = result.get("terminos", [])
        terms_txt = "  • " + "\n  • ".join(esc(t) for t in terms[:6]) if terms else "—"
        await q.edit_message_text(
            f"✅ *{msg}*\n\n"
            f"🔑 Términos usados:\n{terms_txt}\n\n"
            f"El scraping corre en segundo plano. Vuelve en unos minutos.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Mis Vacantes",    callback_data="vacantes:0"),
                 InlineKeyboardButton("📊 Dashboard",       callback_data="dashboard")],
                [InlineKeyboardButton("◀️ Menú Principal",  callback_data="menu")],
            ]),
        )
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ *Error al iniciar búsqueda:*\n`{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )

# ── Generar CV ────────────────────────────────────────────────────────────────

async def _cb_generar(q, ctx, vid: int):
    await q.edit_message_text(
        f"⚙️ Generando CV para vacante *\\#{vid}*...\n"
        f"Esto puede tardar hasta 30 segundos.",
        parse_mode="Markdown",
    )
    try:
        result = await api("POST", f"/generar_cv/{vid}")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ *Error generando CV \\#{vid}:*\n`{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔄 Reintentar", callback_data=f"gen:{vid}")],
                [InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")],
            ]),
        )
        return

    aprobado    = result.get("aprobado", False)
    comentarios = esc(result.get("comentarios", "—"))
    tiene       = result.get("pdf", False)
    p_pdf       = result.get("pdf_path") or pdf_path(vid)
    p_tex       = result.get("tex_path") or tex_path(vid)

    if aprobado and tiene and os.path.exists(p_pdf):
        await q.edit_message_text(
            f"✅ *CV aprobado por Inspector IA*\n\n💬 _{comentarios}_\n\n🟡 Status → *Revisado\\_IA*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Ver PDF",          callback_data=f"pdf:{vid}"),
                 InlineKeyboardButton("📝 Editar LaTeX",     callback_data=f"tex:{vid}")],
                [InlineKeyboardButton("✅ Marcar Listo",     callback_data=f"listo:{vid}")],
                [InlineKeyboardButton("◀️ Menú Principal",   callback_data="menu")],
            ]),
        )
        with open(p_pdf, "rb") as f:
            await q.message.reply_document(
                document=f,
                filename=os.path.basename(p_pdf),
                caption=f"📄 CV Vacante #{vid}",
            )
    elif not aprobado:
        await q.edit_message_text(
            f"⚠️ *Inspector IA: requiere correcciones*\n\n📋 {comentarios}\n\n🔴 Status → *Requiere\\_Correccion*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🚀 Regenerar #{vid}", callback_data=f"gen:{vid}")],
                [InlineKeyboardButton("◀️ Menú Principal",    callback_data="menu")],
            ]),
        )
    else:
        await q.edit_message_text(
            f"⚠️ Inspector IA aprobó pero el PDF no compiló.\n\n💬 _{comentarios}_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Editar LaTeX", callback_data=f"tex:{vid}")],
                [InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")],
            ]),
        )
        if os.path.exists(p_tex):
            with open(p_tex, "rb") as f:
                await q.message.reply_document(
                    document=f,
                    filename=os.path.basename(p_tex),
                    caption="LaTeX aprobado — compila manualmente",
                )

# ── Ver / Enviar PDF ──────────────────────────────────────────────────────────

async def _cb_enviar_pdf(q, vid: int):
    p = pdf_path(vid)
    if not os.path.exists(p):
        await q.answer(f"❌ PDF no encontrado para #{vid}. ¿Ya fue compilado?", show_alert=True)
        return
    await q.answer()
    with open(p, "rb") as f:
        await q.message.reply_document(
            document=f,
            filename=f"cv_vacante_{vid}.pdf",
            caption=f"📄 CV Vacante #{vid}",
        )

# ── Descargar todos los PDFs ──────────────────────────────────────────────────

async def _cb_dlall(q):
    try:
        all_v = await api("GET", "/vacantes?limit=500")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ Error: `{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back("ia"),
        )
        return

    pdfs = [(v["id"], v.get("titulo", "—")) for v in all_v if has_pdf(v["id"])]

    if not pdfs:
        await q.edit_message_text(
            "📥 No hay PDFs generados para descargar.",
            reply_markup=kb_back("ia"),
        )
        return

    await q.edit_message_text(
        f"📦 Enviando *{len(pdfs)}* PDFs...\n_Esto puede tardar unos momentos._",
        parse_mode="Markdown",
    )

    sent = 0
    for vid, titulo in pdfs:
        p = pdf_path(vid)
        try:
            with open(p, "rb") as f:
                await q.message.reply_document(
                    document=f,
                    filename=f"cv_vacante_{vid}.pdf",
                    caption=f"📄 #{vid} — {titulo[:50]}",
                )
            sent += 1
        except Exception as e:
            log.warning("Error enviando PDF %s: %s", vid, e)

    await q.message.reply_text(
        f"✅ *Descarga masiva completa*\n\n📄 Enviados: *{sent}/{len(pdfs)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")],
        ]),
    )

# ── Editar LaTeX ──────────────────────────────────────────────────────────────

async def _cb_editar_latex(q, ctx, vid: int):
    url  = f"{API_BASE}/latex/{vid}"
    loop = asyncio.get_event_loop()
    try:
        def _get():
            with urllib.request.urlopen(url, timeout=15) as r:
                return r.read().decode("utf-8")
        tex = await loop.run_in_executor(None, _get)
    except Exception as e:
        await q.answer(f"❌ LaTeX no disponible: {e}", show_alert=True)
        return

    ctx.user_data["tex_edit_vid"] = vid
    await q.message.reply_document(
        document=io.BytesIO(tex.encode("utf-8")),
        filename=f"cv_vacante_{vid}.tex",
        caption=(
            f"📝 *Editar LaTeX — Vacante \\#{vid}*\n\n"
            f"1\\. Descarga este archivo\n"
            f"2\\. Edítalo con tu editor de LaTeX\n"
            f"3\\. Envíamelo de vuelta como documento `.tex`\n\n"
            f"El bot detectará automáticamente el ID de la vacante por el nombre del archivo."
        ),
        parse_mode="Markdown",
    )

# ── Marcar listo / Borrar ─────────────────────────────────────────────────────

async def _cb_marcar_listo(q, vid: int):
    try:
        await api("PATCH", f"/vacantes/{vid}/status", {"status": "Listo_Manual"})
        await q.answer("✅ Marcado como Listo_Manual")
        tiene = has_pdf(vid)
        await q.edit_message_text(
            f"🟢 *Vacante \\#{vid} marcada como Listo\\_Manual*\n\n"
            "El dashboard web se actualizará en menos de 2 segundos.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔍 Ver vacante #{vid}", callback_data=f"vac:{vid}")],
                *([[InlineKeyboardButton("📄 Descargar PDF", callback_data=f"pdf:{vid}")]] if tiene else []),
                [InlineKeyboardButton("◀️ Menú Principal", callback_data="menu")],
            ]),
        )
    except RuntimeError as e:
        await q.answer(f"❌ {str(e)[:100]}", show_alert=True)

async def _cb_borrar(q, vid: int):
    try:
        await api("DELETE", f"/vacantes/{vid}")
        await q.answer(f"🗑️ Vacante #{vid} eliminada")
        await q.edit_message_text(
            f"🗑️ *Vacante \\#{vid} eliminada.*\n\nEl dashboard web reflejará el cambio en 2 segundos.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Mis Vacantes",    callback_data="vacantes:0"),
                 InlineKeyboardButton("◀️ Menú Principal",  callback_data="menu")],
            ]),
        )
    except RuntimeError as e:
        await q.answer(f"❌ {str(e)[:100]}", show_alert=True)

# ── Acciones IA ───────────────────────────────────────────────────────────────

async def _cb_clean_confirm(q):
    try:
        all_v = await api("GET", "/vacantes?limit=500")
        n = len(all_v)
    except RuntimeError:
        n = "?"
    await q.edit_message_text(
        f"⚠️ *¿Limpiar DB?*\n\nSe eliminarán *{n} vacantes* de forma permanente.\n"
        "Esta acción *no se puede deshacer*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 Confirmar limpieza", callback_data="ia:clean:ok")],
            [InlineKeyboardButton("◀️ Cancelar",            callback_data="ia")],
        ]),
    )

async def _cb_clean_exec(q):
    try:
        all_v = await api("GET", "/vacantes?limit=500")
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ Error: `{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back(),
        )
        return

    total   = len(all_v)
    deleted = 0
    await q.edit_message_text(
        f"🧹 Eliminando *{total}* vacantes...",
        parse_mode="Markdown",
    )
    for v in all_v:
        try:
            await api("DELETE", f"/vacantes/{v['id']}")
            deleted += 1
        except Exception:
            pass

    await q.edit_message_text(
        f"🧹 *DB limpiada:* *{deleted}/{total}* vacantes eliminadas.",
        parse_mode="Markdown",
        reply_markup=kb_back(),
    )

async def _cb_genall(q, ctx):
    try:
        nc = await api("GET", "/vacantes?status=No_Creado&limit=50")
        rc = await api("GET", "/vacantes?status=Requiere_Correccion&limit=50")
        pendientes = nc + rc
    except RuntimeError as e:
        await q.edit_message_text(
            f"❌ Error obteniendo vacantes: `{esc(str(e))}`",
            parse_mode="Markdown",
            reply_markup=kb_back("ia"),
        )
        return

    if not pendientes:
        await q.edit_message_text(
            "✅ No hay vacantes pendientes de generación.",
            reply_markup=kb_back(),
        )
        return

    await q.edit_message_text(
        f"⚡ Generando CVs para *{len(pendientes)}* vacantes pendientes...\n"
        "Este proceso puede tardar varios minutos.",
        parse_mode="Markdown",
    )

    ok, fail = 0, 0
    for v in pendientes:
        try:
            result = await api("POST", f"/generar_cv/{v['id']}")
            if result.get("aprobado"):
                ok += 1
            else:
                fail += 1
        except Exception:
            fail += 1

    await q.message.reply_text(
        f"⚡ *Generación masiva completada*\n\n"
        f"✅ Aprobados: *{ok}*\n"
        f"❌ Rechazados/error: *{fail}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Mis CVs",         callback_data="cvs:0"),
             InlineKeyboardButton("📋 Mis Vacantes",    callback_data="vacantes:0")],
            [InlineKeyboardButton("◀️ Menú Principal",  callback_data="menu")],
        ]),
    )

# ── Recepción de archivos .tex ────────────────────────────────────────────────

@admin_only
async def handle_tex_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".tex"):
        return

    fname = doc.file_name
    m     = re.match(r"cv_vacante_(\d+)\.tex$", fname, re.IGNORECASE)
    vid   = int(m.group(1)) if m else ctx.user_data.get("tex_edit_vid")

    if not vid:
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
        dest    = os.path.join(TEMPLATES_DIR, "mi_estilo.tex")
        tg_file = await ctx.bot.get_file(doc.file_id)
        await tg_file.download_to_drive(dest)
        await update.message.reply_text(
            "✅ *Plantilla de estilo actualizada.*\n"
            "El próximo CV generado usará tu diseño personalizado.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        f"📝 Guardando y compilando LaTeX para vacante *\\#{vid}*...",
        parse_mode="Markdown",
    )

    buf     = bytearray()
    tg_file = await ctx.bot.get_file(doc.file_id)
    await tg_file.download_to_memory(buf)
    tex_content = bytes(buf).decode("utf-8", errors="replace")

    url  = f"{API_BASE}/latex/{vid}"
    loop = asyncio.get_event_loop()

    def _post():
        body = tex_content.encode("utf-8")
        req  = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    try:
        result = await loop.run_in_executor(None, _post)
    except Exception as e:
        await update.message.reply_text(f"❌ Error al guardar LaTeX: {esc(str(e))}", parse_mode="Markdown")
        ctx.user_data.pop("tex_edit_vid", None)
        return

    if result.get("pdf"):
        await update.message.reply_text(
            f"✅ *LaTeX guardado y PDF compilado correctamente.*",
            parse_mode="Markdown",
        )
        p = pdf_path(vid)
        if os.path.exists(p):
            with open(p, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"cv_vacante_{vid}.pdf",
                    caption=f"PDF actualizado — Vacante #{vid}",
                )
    else:
        err = esc((result.get("error") or "Error desconocido.")[:300])
        await update.message.reply_text(
            f"⚠️ .tex guardado pero el PDF no compiló:\n`{err}`",
            parse_mode="Markdown",
        )

    ctx.user_data.pop("tex_edit_vid", None)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("ERROR: Configura TELEGRAM_BOT_TOKEN en job_hunter/.env")
        return

    if not ADMIN_ID:
        print("⚠️  ADVERTENCIA: TELEGRAM_ADMIN_ID no configurado — cualquiera puede usar el bot.")
    else:
        print(f"✓ Admin ID: {ADMIN_ID}")

    print(f"✓ API target: {API_BASE}")
    heartbeat_api()
    start_heartbeat()

    conf = load_conf()

    app = Application.builder().token(TOKEN).build()
    app.bot_data["auto_scrape"] = conf.get("auto_scrape", False)
    app.bot_data["debug_mode"]  = conf.get("debug_mode",  False)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_menu))
    app.add_handler(CommandHandler("cvs",   cmd_cvs))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_tex_upload))

    print("✓ Job Hunter Bot en línea. Ctrl+C para detener.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
