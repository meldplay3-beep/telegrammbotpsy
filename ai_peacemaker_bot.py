import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import openai

# Логи
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise SystemExit("TELEGRAM_TOKEN и OPENAI_API_KEY должны быть установлены в переменных окружения")

openai.api_key = OPENAI_API_KEY

# Хранилище имен пользователей
users = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "Привет 🌿 Я твой дружелюбный помощник. Как мне к тебе обращаться?"
    )

# Команда /setname
async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = " ".join(context.args)
    if name:
        users[user_id] = name
        await update.message.reply_text(f"Отлично, я буду обращаться к тебе {name} 🌸")
    else:
        await update.message.reply_text("Напиши имя после команды /setname Имя")

# Команда /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Хорошо, делаем паузу 🌿")

# Основной обработчик всех сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = users.get(user_id, "друг")
    user_text = update.message.text

    prompt = f"""
Ты дружелюбный и понимающий AI-помощник.
Твоя задача — помочь человеку успокоиться после ссоры, разобрать ситуацию и мягко вести к примирению.
Ты отвечаешь только доброжелательно и человечно.
Обращайся к пользователю по имени {user_name}.
Пользователь пишет: "{user_text}"
Дай поддержку, разбор ситуации и советы, как успокоиться и найти путь к примирению.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=500
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("Упс, что-то пошло не так 😅 Попробуй через минуту.")

# Основная функция
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setname", set_name))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()