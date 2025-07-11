import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Подключение к базе данных
conn = sqlite3.connect("participants.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS participants (user_id INTEGER PRIMARY KEY, username TEXT)")
conn.commit()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Участвовать", callback_data="join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Нажми кнопку, чтобы участвовать в розыгрыше:",
        reply_markup=reply_markup
    )

# Обработка кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    # Проверка подписки
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await context.bot.send_message(user.id, "❌ Вы не подписаны на канал!")
            return
    except Exception as e:
        await context.bot.send_message(user.id, "❌ Не удалось проверить подписку.")
        return

    # Добавление в БД
    try:
        cursor.execute("INSERT INTO participants (user_id, username) VALUES (?, ?)", (user.id, user.username))
        conn.commit()
        await context.bot.send_message(user.id, "🎉 Вы успешно участвуете в розыгрыше!")
    except sqlite3.IntegrityError:
        await context.bot.send_message(user.id, "🔁 Вы уже участвуете в розыгрыше.")

# Команда выбора победителя (только для админа)
async def choose_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != ADMIN_USERNAME:
        await update.message.reply_text("⛔ Только админ может выбирать победителя.")
        return

    cursor.execute("SELECT user_id, username FROM participants ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()

    if result:
        user_id, username = result
        message = f"🏆 Победитель розыгрыша: @{username} (ID: {user_id})"
        await update.message.reply_text("✅ Победитель выбран.")
        # Рассылка всем
        cursor.execute("SELECT user_id FROM participants")
        for row in cursor.fetchall():
            try:
                await context.bot.send_message(row[0], message)
            except:
                pass
    else:
        await update.message.reply_text("❗ Нет участников.")

# Запуск бота
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("winner", choose_winner))
app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    print("🤖 Бот Rndm запущен...")
    app.run_polling()
