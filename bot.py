import os
import logging
import random
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)

# Настройка логов
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка токена
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise SystemExit("Please set TELEGRAM_TOKEN in Environment Variables")

# Настройка базы данных
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            situation TEXT,
            feelings TEXT,
            values TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user_name(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_user_name(user_id: int, name: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = excluded.name", (user_id, name))
    conn.commit()
    conn.close()

def save_reflection(user_id: int, situation: str, feelings: str, values: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reflections (user_id, situation, feelings, values, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, situation, feelings, values, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# Состояния для ConversationHandler
ASK_NAME, CALM_TALK, REFLECT_Q1, REFLECT_Q2, REFLECT_Q3 = range(5)

# Дыхательные упражнения и аффирмации
BREATHING_TIPS = [
    "Вдохни глубоко на 4 сек... задержи дыхание на 4... и медленно выдохни на 6 🌬",
    "Закрой глаза и сделай 3 медленных глубоких вдоха 🌿",
    "Попробуй дыхание 'коробочка': вдох 4 сек — задержка 4 сек — выдох 4 сек — задержка 4 сек 🔲"
]

AFFIRMATIONS = [
    "Ты сильнее, чем думаешь 💙",
    "Ты заслуживаешь любви и спокойствия 🌸",
    "Ты справишься, я рядом 🙏",
    "Каждый шаг к миру важен 🌟"
]

def get_name_from_db(user_id: int) -> str:
    name = get_user_name(user_id)
    return name if name else "друг"

# Хэндлеры
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = get_user_name(user_id)
    if not name:
        await update.message.reply_text("Привет 🌿 Я твой бот-друг. Как мне к тебе обращаться?")
        return ASK_NAME
    else:
        await update.message.reply_text(
            f"Снова рад тебя видеть, {name} 💙\nКоманды:\n• /calm — режим успокоения\n• /reflect — разбор ситуации\n• /setname — изменить имя\n• /cancel — прервать разговор"
        )
        return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = update.message.text.strip()
    set_user_name(user_id, name)
    await update.message.reply_text(f"Рад познакомиться, {name} 🌸")
    return ConversationHandler.END

async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    await update.message.reply_text("Хорошо 🌿 Напиши, как мне к тебе обращаться.")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Хорошо, сделаем паузу. Я рядом 🌸")
    return ConversationHandler.END

async def calm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = get_name_from_db(user_id)
    await update.message.reply_text(f"Я понимаю, тебе сейчас непросто, {name} 💙\nРасскажи, что на душе.")
    return CALM_TALK

async def calm_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = get_name_from_db(user_id)
    tip = random.choice(BREATHING_TIPS)
    affirm = random.choice(AFFIRMATIONS)
    await update.message.reply_text(f"{tip}\n\n{affirm}")
    return ConversationHandler.END

async def reflect_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = get_name_from_db(user_id)
    await update.message.reply_text(f"{name} 💫\n1/3. Что произошло в ссоре?")
    return REFLECT_Q1

async def reflect_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["situation"] = update.message.text
    await update.message.reply_text("2/3. Что ты чувствовал(а)? ❤️")
    return REFLECT_Q2

async def reflect_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["feelings"] = update.message.text
    await update.message.reply_text("3/3. Что хорошего ты ценишь в партнёре? 🌸")
    return REFLECT_Q3

async def reflect_q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = get_name_from_db(user_id)
    situation = context.user_data.get("situation", "")
    feelings = context.user_data.get("feelings", "")
    values = update.message.text
    save_reflection(user_id, situation, feelings, values)
    await update.message.reply_text(f"Спасибо, {name} 💙\nТы рассказал(а):\nСитуация: {situation}\nЧувства: {feelings}\nЦенность: {values}")
    return ConversationHandler.END

def main() -> None:
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    name_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(name_conv)
    app.add_handler(CommandHandler("setname", setname))

    calm_conv = ConversationHandler(
        entry_points=[CommandHandler("calm", calm_entry)],
        states={CALM_TALK: [MessageHandler(filters.TEXT & ~filters.COMMAND, calm_talk)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(calm_conv)

    reflect_conv = ConversationHandler(
        entry_points=[CommandHandler("reflect", reflect_entry)],
        states={
            REFLECT_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q1)],
            REFLECT_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q2)],
            REFLECT_Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q3)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(reflect_conv)
    app.add_handler(CommandHandler("cancel", cancel))

    app.run_polling()

if __name__ == "__main__":
    main()