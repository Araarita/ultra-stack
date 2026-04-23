"""Ultra Telegram Bot - Letta memory + LLM Router."""
import sys
sys.path.insert(0, "/opt/ultra")
import os
import logging
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from letta_client import Letta, MessageCreate
from shared.llm_router.router import get_current_mode, set_mode, get_mode_status, list_all_modes, MODE_INFO

load_dotenv("/opt/ultra/.env")
BOT_TOKEN = os.getenv("TELEGRAM_ULTRA_BOT_TOKEN")
OWNER_ID = int(os.getenv("TELEGRAM_OWNER_CHAT_ID", "0"))
letta = Letta(base_url="http://localhost:8283")
AGENT_ID = "agent-ea61e976-a19f-49d4-b4f3-1e66214b1258"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def is_owner(update):
    return update.effective_user.id == OWNER_ID


async def start(update, context):
    if not is_owner(update):
        await update.message.reply_text("Acceso denegado.")
        return
    mode = get_current_mode()
    info = MODE_INFO[mode]
    await update.message.reply_text(
        f"Ultra AI activo\n\nModo: {info['emoji']} {mode}\n{info['intelligence']} | {info['cost_level']}\n\n"
        f"Comandos:\n/status - modo actual\n/modes - lista\n/free /normal /kimi - cambiar modo\n"
        f"/boost pass /turbo pass - premium\n\nEscribeme lo que quieras"
    )


async def status(update, context):
    if not is_owner(update): return
    s = get_mode_status()
    msg = f"{s['emoji']} Modo actual: {s['mode']}\n\n{s['intelligence']} | {s['cost_level']}\n{s['description']}\n\nCosto: {s['avg_cost']}\nVelocidad: {s['speed']}\n\nModelos:\n"
    for task, model in list(s['models'].items())[:5]:
        msg += f"- {task}: {model}\n"
    await update.message.reply_text(msg)


async def modes(update, context):
    if not is_owner(update): return
    msg = "Los 5 modos:\n\n"
    for m in list_all_modes():
        lock = "[P]" if m["password_required"] else "   "
        msg += f"{m['emoji']} {lock} {m['mode']} {m['intelligence']} {m['cost_level']}\n   {m['description']}\n\n"
    await update.message.reply_text(msg)


async def change_mode(update, context):
    if not is_owner(update): return
    cmd = update.message.text.split()[0].replace("/", "").upper()
    pwd = context.args[0] if context.args else None
    result = set_mode(cmd, pwd)
    if result["ok"]:
        await update.message.reply_text(
            f"{result['emoji']} {result['mode']} activo\n\n{result['description']}\n{result['intelligence']} | Costo: {result['cost']}"
        )
    else:
        await update.message.reply_text(f"Error: {result['error']}")


async def handle_message(update, context):
    if not is_owner(update):
        await update.message.reply_text("Acceso denegado.")
        return
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = letta.agents.messages.create(
            agent_id=AGENT_ID,
            messages=[MessageCreate(role="user", content=user_message)]
        )
        replies = []
        for msg in response.messages:
            c = getattr(msg, "content", None)
            if c:
                if isinstance(c, str):
                    replies.append(c)
                elif isinstance(c, list):
                    for item in c:
                        t = getattr(item, "text", None)
                        if t: replies.append(t)
        reply_text = "\n".join(replies) if replies else "(sin respuesta)"
        if len(reply_text) > 4000:
            for i in range(0, len(reply_text), 4000):
                await update.message.reply_text(reply_text[i:i+4000])
        else:
            await update.message.reply_text(reply_text)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"Error: {str(e)[:200]}")



# ============================================
# COMANDOS DE CREWS
# ============================================
from crews.research.research_crew import run_research
import threading
import asyncio

active_crews = {}  # Trackea crews corriendo

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/research <topic> - Ejecuta el Research Crew."""
    if not is_owner(update): return
    
    if not context.args:
        await update.message.reply_text(
            "Uso: /research <tema>\n\n"
            "Ejemplo: /research Tendencias IA 2026"
        )
        return
    
    topic = " ".join(context.args)
    user_id = update.effective_user.id
    
    # Avisar que empieza
    msg = await update.message.reply_text(
        f"Research Crew activado\n\n"
        f"Tema: {topic}\n"
        f"Agentes: Scout + Curator + Synthesizer\n"
        f"Tiempo estimado: 3-6 minutos\n\n"
        f"Te aviso cuando termine con el reporte completo"
    )
    
    # Ejecutar en thread para no bloquear el bot
    def run_in_thread():
        try:
            result = run_research(topic)
            
            # Guardar reporte
            import os
            os.makedirs("/opt/ultra/data/reportes", exist_ok=True)
            safe_name = topic.replace(" ", "_")[:50]
            report_path = f"/opt/ultra/data/reportes/{safe_name}.md"
            with open(report_path, "w") as f:
                f.write(f"# Reporte: {topic}\n\n{result}")
            
            # Enviar a Telegram (dividido si es muy largo)
            asyncio.run(send_report(context.bot, update.effective_chat.id, topic, result, report_path))
        except Exception as e:
            asyncio.run(context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Error en research: {str(e)[:300]}"
            ))
    
    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    active_crews[user_id] = thread

async def send_report(bot, chat_id, topic, result, path):
    """Envía el reporte por Telegram."""
    header = f"Research completado\n\nTema: {topic}\nGuardado en: {path}\n\n"
    await bot.send_message(chat_id=chat_id, text=header)
    
    # Enviar el reporte en chunks de 4000 chars
    result_str = str(result)
    for i in range(0, len(result_str), 4000):
        chunk = result_str[i:i+4000]
        try:
            await bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            print(f"Error enviando chunk: {e}")


async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Iniciar Ultra"),
        BotCommand("status", "Modo actual"),
        BotCommand("modes", "Lista de modos"),
        BotCommand("free", "Modo gratis"),
        BotCommand("normal", "Modo normal"),
        BotCommand("kimi", "Modo Kimi"),
        BotCommand("boost", "Modo Boost (pass)"),
        BotCommand("turbo", "Modo Turbo (pass)"),
        BotCommand("research", "Investigar un tema (Research Crew)"),
    ])


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_ULTRA_BOT_TOKEN no configurado")
        return
    logger.info(f"Iniciando Ultra Bot (Owner: {OWNER_ID})")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("modes", modes))
    app.add_handler(CommandHandler(["free", "normal", "kimi", "boost", "turbo"], change_mode))
    app.add_handler(CommandHandler("research", research_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot corriendo - busca tu bot en Telegram y manda /start")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
