import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
import subprocess
import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, ContextTypes
)
from gemini_engine import generar_y_compilar, TEMPLATES_DIR, OUTPUTS_DIR
from inspector import evaluar_cv

TOKEN = "8987674164:AAG0pnCvhXcII0ZncPHXOYIlKalw2eOdA7E"
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'vacantes.db')

VALID_STATUSES = {"No_Creado", "En_Proceso", "Revisado_IA", "Listo_Manual", "Requiere_Correccion"}

ASK_TITULO, ASK_EMPRESA, ASK_ENLACE, ASK_REQS = range(4)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# ── Helpers DB ────────────────────────────────────────────────────────────────

def db():
    return sqlite3.connect(DB_PATH)

def fmt_status(s):
    icons = {
        "No_Creado": "⬜", "En_Proceso": "🔵",
        "Revisado_IA": "🟡", "Listo_Manual": "🟢", "Requiere_Correccion": "🔴"
    }
    return f"{icons.get(s, '❓')} {s}"

# ── /menu ─────────────────────────────────────────────────────────────────────

async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Buscar Vacantes", callback_data="buscar_3")],
        [InlineKeyboardButton("📋 Ver Pendientes",  callback_data="pendientes")],
        [InlineKeyboardButton("⚙️ Resumen",         callback_data="resumen")],
    ])
    await update.message.reply_text(
        "*Job Hunter — Menú Principal*",
        parse_mode="Markdown",
        reply_markup=kb,
    )

# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "*Job Hunter Bot* 🤖\n\n"
        "/menu — menú interactivo con botones\n"
        "/vacantes — últimas 10 vacantes\n"
        "/detalles <ID> — ver requerimientos\n"
        "/estado <ID> <ESTADO> — cambiar status\n"
        "/agregar\\_manual — añadir vacante manual\n"
        "/buscar <cantidad> — búsqueda autónoma (ej. /buscar 5)\n\n"
        "Estados válidos: `No_Creado` `En_Proceso` `Revisado_IA` `Listo_Manual`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /vacantes ─────────────────────────────────────────────────────────────────

async def cmd_vacantes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conn = db()
    rows = conn.execute(
        "SELECT id, titulo, empresa, compatibilidad, status "
        "FROM vacantes ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No hay vacantes registradas.")
        return

    lines = ["*Últimas 10 vacantes:*\n"]
    for r in rows:
        compat_icon = {"Alta": "🔥", "Media": "🟠", "Baja": "🔵", "Nula": "⚪"}.get(r[3], "❓")
        lines.append(
            f"`[{r[0]:>3}]` {compat_icon} *{r[1][:40]}*\n"
            f"       _{r[2][:30]}_ — {fmt_status(r[4])}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── /detalles <ID> ────────────────────────────────────────────────────────────

async def cmd_detalles(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Uso: /detalles <ID>")
        return
    try:
        vid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("ID debe ser un número.")
        return

    conn = db()
    row = conn.execute(
        "SELECT titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro "
        "FROM vacantes WHERE id=?", (vid,)
    ).fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(f"Vacante #{vid} no encontrada.")
        return

    titulo, empresa, enlace, reqs, compat, status, fecha = row
    reqs_preview = (reqs[:800] + "…") if reqs and len(reqs) > 800 else (reqs or "Sin datos")
    msg = (
        f"*#{vid} — {titulo}*\n"
        f"🏢 {empresa}\n"
        f"📅 {fecha[:10]}\n"
        f"🎯 Compat: *{compat}* | {fmt_status(status)}\n"
        f"🔗 {enlace}\n\n"
        f"📋 *Requerimientos:*\n{reqs_preview}"
    )

    kb = _vacante_keyboard(vid, status)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

def _vacante_keyboard(vid: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status in ("No_Creado", "Requiere_Correccion", "En_Proceso"):
        buttons.append(InlineKeyboardButton("🚀 Generar con Groq", callback_data=f"gen_{vid}"))
    if status == "Revisado_IA":
        buttons.append(InlineKeyboardButton("📄 Descargar PDF", callback_data=f"pdf_{vid}"))
    buttons.append(InlineKeyboardButton("✅ Marcar Listo", callback_data=f"listo_{vid}"))
    return InlineKeyboardMarkup([buttons])

# ── /estado <ID> <ESTADO> ────────────────────────────────────────────────────

async def cmd_estado(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Uso: /estado <ID> <NUEVO_ESTADO>")
        return
    try:
        vid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("ID debe ser un número.")
        return

    nuevo = ctx.args[1].strip()
    if nuevo not in VALID_STATUSES:
        await update.message.reply_text(
            f"Estado inválido. Usa:\n" + "\n".join(f"`{s}`" for s in VALID_STATUSES),
            parse_mode="Markdown"
        )
        return

    conn = db()
    conn.execute("UPDATE vacantes SET status=? WHERE id=?", (nuevo, vid))
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()

    if changes:
        await update.message.reply_text(f"✅ Vacante #{vid} → {fmt_status(nuevo)}")
    else:
        await update.message.reply_text(f"Vacante #{vid} no encontrada.")

# ── ConversationHandler: /agregar_manual ─────────────────────────────────────

async def manual_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("📝 *Agregar vacante manual*\n\nTítulo del puesto:", parse_mode="Markdown")
    return ASK_TITULO

async def manual_titulo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['titulo'] = update.message.text.strip()
    await update.message.reply_text("Empresa:")
    return ASK_EMPRESA

async def manual_empresa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['empresa'] = update.message.text.strip() or "Desconocida"
    await update.message.reply_text("Enlace (URL de la vacante):")
    return ASK_ENLACE

async def manual_enlace(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['enlace'] = update.message.text.strip()
    await update.message.reply_text("Requerimientos / descripción del puesto:")
    return ASK_REQS

async def manual_reqs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['reqs'] = update.message.text.strip()
    d = ctx.user_data

    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO vacantes (titulo, empresa, enlace, requerimientos, compatibilidad, status) "
        "VALUES (?,?,?,?,?,'No_Creado')",
        (d['titulo'][:200], d['empresa'][:100], d['enlace'], d['reqs'][:2000], "Nula")
    )
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    row_id  = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    if changes:
        await update.message.reply_text(
            f"✅ Vacante guardada con ID *#{row_id}*\n_{d['titulo'][:60]}_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ Enlace duplicado. La vacante ya existe.")

    ctx.user_data.clear()
    return ConversationHandler.END

async def manual_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

# ── /buscar <cantidad> ───────────────────────────────────────────────────────

async def cmd_buscar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Uso: /buscar <cantidad>\nEjemplo: `/buscar 5`",
            parse_mode="Markdown"
        )
        return
    try:
        cantidad = int(ctx.args[0])
        if cantidad < 1 or cantidad > 200:
            raise ValueError
    except ValueError:
        await update.message.reply_text("La cantidad debe ser un número entre 1 y 200.")
        return

    await update.message.reply_text(
        f"🔍 Iniciando búsqueda autónoma de *{cantidad}* vacantes...\n"
        f"Esto puede tardar varios minutos.",
        parse_mode="Markdown"
    )

    agent_path = os.path.join(os.path.dirname(__file__), 'browser_agent.py')
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, agent_path, '--limit', str(cantidad)],
                timeout=600,
            )
        )
        await update.message.reply_text(
            f"✅ Búsqueda completada. Se solicitaron *{cantidad}* vacantes.\n"
            f"Usa /vacantes para ver los nuevos registros.",
            parse_mode="Markdown"
        )
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱ El scraping superó el tiempo límite (10 min).")
    except Exception as e:
        await update.message.reply_text(f"❌ Error en la búsqueda: {e}")

# ── /generar_cv <ID> ─────────────────────────────────────────────────────────

async def cmd_generar_cv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Uso: /generar_cv <ID>")
        return
    try:
        vid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("ID debe ser un número.")
        return

    conn = db()
    row = conn.execute("SELECT titulo, empresa FROM vacantes WHERE id=?", (vid,)).fetchone()
    conn.close()
    if not row:
        await update.message.reply_text(f"Vacante #{vid} no encontrada.")
        return

    titulo, empresa = row
    await update.message.reply_text(
        f"⚙️ Generando CV para:\n*#{vid} — {titulo}*\n_{empresa}_\n\nEsto puede tomar ~30s...",
        parse_mode="Markdown"
    )

    loop = asyncio.get_event_loop()
    try:
        tex_path, pdf_path = await loop.run_in_executor(None, generar_y_compilar, vid)
    except ValueError as e:
        await update.message.reply_text(f"❌ Config error: {e}")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ Error inesperado: {e}")
        return

    if not tex_path:
        await update.message.reply_text("❌ Falló la generación. Verifica la API key de IA y la vacante.")
        return

    await update.message.reply_text("🔍 Auditando CV con IA Inspector...")
    auditoria = await loop.run_in_executor(None, evaluar_cv, vid, tex_path)
    aprobado    = auditoria["aprobado"]
    comentarios = auditoria["comentarios"]

    conn = db()
    if aprobado and pdf_path and os.path.exists(pdf_path):
        conn.execute("UPDATE vacantes SET status='Revisado_IA' WHERE id=?", (vid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"✅ *CV aprobado por Inspector IA*\n\n"
            f"💬 _{comentarios}_\n\n"
            f"🟡 Status → *Revisado_IA*",
            parse_mode="Markdown"
        )
        with open(pdf_path, 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=os.path.basename(pdf_path),
                caption=f"CV aprobado: {titulo[:50]}"
            )
    elif not aprobado:
        conn.execute("UPDATE vacantes SET status='Requiere_Correccion' WHERE id=?", (vid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"⚠️ *Inspector IA: CV requiere correcciones*\n\n"
            f"📋 *Comentarios:*\n{comentarios}\n\n"
            f"🔴 Status → *Requiere_Correccion*\n"
            f"Usa `/generar_cv {vid}` para regenerar.",
            parse_mode="Markdown"
        )
    else:
        conn.execute("UPDATE vacantes SET status='Revisado_IA' WHERE id=?", (vid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(
            f"⚠️ *Inspector IA aprobó el CV* pero PDF no compiló.\n\n"
            f"💬 _{comentarios}_\n\n"
            f"Enviando .tex para revisión manual:",
            parse_mode="Markdown"
        )
        with open(tex_path, 'rb') as tex_file:
            await update.message.reply_document(
                document=tex_file,
                filename=os.path.basename(tex_path),
                caption="LaTeX aprobado — compila manualmente"
            )

# ── Recepción de archivo .tex como plantilla ─────────────────────────────────

async def handle_tex_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.tex'):
        return

    dest = os.path.join(TEMPLATES_DIR, 'mi_estilo.tex')
    tg_file = await ctx.bot.get_file(doc.file_id)
    await tg_file.download_to_drive(dest)

    await update.message.reply_text(
        "✅ *¡Plantilla visual actualizada con éxito!*\n"
        f"Guardada en: `latex_templates/mi_estilo.tex`\n\n"
        "El próximo `/generar_cv` usará tu diseño personalizado.",
        parse_mode="Markdown"
    )

# ── Acciones inline (helpers) ─────────────────────────────────────────────────

async def _send_pendientes(message):
    conn = db()
    rows = conn.execute(
        "SELECT id, titulo, empresa, compatibilidad, status FROM vacantes "
        "WHERE status IN ('No_Creado','Requiere_Correccion') "
        "ORDER BY id DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not rows:
        await message.reply_text("No hay vacantes pendientes.")
        return

    await message.reply_text(
        f"📋 *Vacantes pendientes ({len(rows)}):*",
        parse_mode="Markdown"
    )
    for r in rows:
        vid, titulo, empresa, compat, status = r
        compat_icon = {"Alta": "🔥", "Media": "🟠", "Baja": "🔵", "Nula": "⚪"}.get(compat, "❓")
        text = (
            f"`#{vid}` {compat_icon} *{titulo[:40]}*\n"
            f"_{empresa[:30]}_ — {fmt_status(status)}"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Generar", callback_data=f"gen_{vid}"),
            InlineKeyboardButton("✅ Marcar Listo", callback_data=f"listo_{vid}"),
        ]])
        await message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def _send_resumen(message):
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM vacantes").fetchone()[0]
    por_status = conn.execute("SELECT status, COUNT(*) FROM vacantes GROUP BY status").fetchall()
    por_compat = conn.execute(
        "SELECT compatibilidad, COUNT(*) FROM vacantes GROUP BY compatibilidad"
    ).fetchall()
    conn.close()

    status_lines = "\n".join(f"  {fmt_status(s)}: {c}" for s, c in por_status)
    compat_lines = "\n".join(f"  {k}: {v}" for k, v in por_compat)

    await message.reply_text(
        f"⚙️ *Resumen de la DB*\n\n"
        f"Total vacantes: *{total}*\n\n"
        f"*Por status:*\n{status_lines}\n\n"
        f"*Por compatibilidad:*\n{compat_lines}",
        parse_mode="Markdown"
    )


async def _accion_generar(message, vid: int):
    conn = db()
    row = conn.execute("SELECT titulo, empresa FROM vacantes WHERE id=?", (vid,)).fetchone()
    conn.close()
    if not row:
        await message.reply_text(f"Vacante #{vid} no encontrada.")
        return

    titulo, empresa = row
    await message.reply_text(
        f"⚙️ Generando CV para *#{vid} — {titulo}*...\nEsto puede tomar ~30 s.",
        parse_mode="Markdown"
    )

    loop = asyncio.get_event_loop()
    try:
        tex_path, pdf_path = await loop.run_in_executor(None, generar_y_compilar, vid)
    except Exception as e:
        await message.reply_text(f"❌ Error generando CV: {e}")
        return

    if pdf_path and os.path.exists(pdf_path):
        conn = db()
        conn.execute("UPDATE vacantes SET status='Revisado_IA' WHERE id=?", (vid,))
        conn.commit()
        conn.close()
        await message.reply_text(f"✅ CV generado para #{vid}. Status → Revisado_IA")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📄 Descargar PDF", callback_data=f"pdf_{vid}")
        ]])
        await message.reply_text("¿Descargar el PDF?", reply_markup=kb)
    else:
        await message.reply_text("⚠️ .tex guardado pero PDF no compiló. Revisa la sintaxis LaTeX.")


async def _accion_pdf(message, vid: int):
    pdf_path = os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.pdf")
    if not os.path.exists(pdf_path):
        await message.reply_text(f"PDF no encontrado para vacante #{vid}. ¿Ya fue compilado?")
        return
    with open(pdf_path, 'rb') as f:
        await message.reply_document(document=f, filename=f"cv_vacante_{vid}.pdf",
                                     caption=f"CV Vacante #{vid}")


async def _accion_listo(message, vid: int):
    conn = db()
    conn.execute("UPDATE vacantes SET status='Listo_Manual' WHERE id=?", (vid,))
    conn.commit()
    changes = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    if changes:
        await message.reply_text(f"✅ Vacante #{vid} → {fmt_status('Listo_Manual')}")
    else:
        await message.reply_text(f"Vacante #{vid} no encontrada.")

# ── CallbackQueryHandler ──────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    msg   = query.message

    if data == "buscar_3":
        await msg.reply_text("🔍 Iniciando búsqueda de 3 vacantes. Esto puede tardar varios minutos...")
        agent_path = os.path.join(os.path.dirname(__file__), 'browser_agent.py')
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.run([sys.executable, agent_path, '--limit', '3'], timeout=600)
            )
            await msg.reply_text("✅ Búsqueda completada. Usa 📋 Ver Pendientes para ver las nuevas.")
        except subprocess.TimeoutExpired:
            await msg.reply_text("⏱ El scraping superó el tiempo límite (10 min).")
        except Exception as e:
            await msg.reply_text(f"❌ Error: {e}")

    elif data == "pendientes":
        await _send_pendientes(msg)

    elif data == "resumen":
        await _send_resumen(msg)

    elif data.startswith("gen_"):
        vid = int(data.split("_", 1)[1])
        await _accion_generar(msg, vid)

    elif data.startswith("pdf_"):
        vid = int(data.split("_", 1)[1])
        await _accion_pdf(msg, vid)

    elif data.startswith("listo_"):
        vid = int(data.split("_", 1)[1])
        await _accion_listo(msg, vid)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if TOKEN == "TU_TOKEN_AQUI":
        print("ERROR: Reemplaza TU_TOKEN_AQUI con el token real de @BotFather")
        return

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("agregar_manual", manual_start)],
        states={
            ASK_TITULO:  [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_titulo)],
            ASK_EMPRESA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_empresa)],
            ASK_ENLACE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_enlace)],
            ASK_REQS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_reqs)],
        },
        fallbacks=[CommandHandler("cancelar", manual_cancel)],
    )

    app.add_handler(CommandHandler("start",        cmd_start))
    app.add_handler(CommandHandler("menu",         cmd_menu))
    app.add_handler(CommandHandler("vacantes",     cmd_vacantes))
    app.add_handler(CommandHandler("detalles",     cmd_detalles))
    app.add_handler(CommandHandler("estado",       cmd_estado))
    app.add_handler(CommandHandler("generar_cv",   cmd_generar_cv))
    app.add_handler(CommandHandler("buscar",       cmd_buscar))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_tex_upload))

    print("✓ Bot iniciado. Ctrl+C para detener.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
