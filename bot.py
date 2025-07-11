import os
import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

conn = sqlite3.connect("participants.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS participants (
    user_id INTEGER PRIMARY KEY,
    username TEXT
)
""")
conn.commit()

# Меню клавиатура
def main_menu(is_admin: bool):
    buttons = [
        [InlineKeyboardButton("🎁 Участвовать", callback_data="join")],
        [InlineKeyboardButton("👥 Участники", callback_data="members")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("🏆 Выбрать победителя", callback_data="winner")])
    return InlineKeyboardMarkup(buttons)

# Команда /start - показать меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = (user.username == ADMIN_USERNAME)
    await update.message.reply_text(
        "👋 Добро пожаловать! Выберите действие ниже:",
        reply_markup=main_menu(is_admin)
    )

# Обработка нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    is_admin = (user.username == ADMIN_USERNAME)
    await query.answer()

    if query.data == "join":
        # Проверяем подписку на канал
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await context.bot.send_message(user.id, "❌ Вы должны подписаться на канал, чтобы участвовать.")
                return
        except Exception:
            await context.bot.send_message(user.id, "⚠️ Не удалось проверить подписку. Попробуйте позже.")
            return

        try:
            cursor.execute("INSERT INTO participants (user_id, username) VALUES (?, ?)", (user.id, user.username))
            conn.commit()
            await context.bot.send_message(user.id, "🎉 Вы успешно зарегистрировались для участия!")
        except sqlite3.IntegrityError:
            await context.bot.send_message(user.id, "🔁 Вы уже участвуете в розыгрыше.")

    elif query.data == "members":
        cursor.execute("SELECT COUNT(*) FROM participants")
        count = cursor.fetchone()[0]
        await context.bot.send_message(user.id, f"👥 Сейчас участвует: {count} человек.")

    elif query.data == "winner":
        if not is_admin:
            await context.bot.send_message(user.id, "⛔ Эта кнопка доступна только админу.")
            return

        cursor.execute("SELECT user_id, username FROM participants ORDER BY RANDOM() LIMIT 1")
        winner = cursor.fetchone()
        if winner:
            winner_id, winner_username = winner
            text = f"🏆 Победитель: @{winner_username or 'без ника'} (ID: {winner_id})"
            await context.bot.send_message(user.id, text)

            # Отправляем всем участникам сообщение с победителем
            cursor.execute("SELECT user_id FROM participants")
            participants = cursor.fetchall()
            for (uid,) in participants:
                try:
                    await context.bot.send_message(uid, text)
                except:
                    pass
        else:
            await context.bot.send_message(user.id, "❗ Нет участников для выбора победителя.")

    # После любого действия показываем меню снова
    if query.message:
        await query.message.edit_reply_markup(reply_markup=main_menu(is_admin))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Бот запущен")
    app.run_polling()
