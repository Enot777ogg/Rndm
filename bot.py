import os
import logging
import datetime
import random
import aiosqlite

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import Forbidden
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

logging.basicConfig(level=logging.INFO)


async def init_db():
    async with aiosqlite.connect("lottery.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                chat_id INTEGER,
                joined_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                method TEXT,
                picked_at TEXT
            )
        """)
        await db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✅ Участвовать", callback_data='join')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Нажми кнопку ниже, чтобы участвовать в розыгрыше:",
        reply_markup=reply_markup
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Участвовать", callback_data='join')],
        [InlineKeyboardButton("👥 Список участников", callback_data='list')],
        [InlineKeyboardButton("🎯 Розыгрыш", callback_data='pick')],
        [InlineKeyboardButton("🔁 Сброс", callback_data='reset')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Меню управления:", reply_markup=reply_markup)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat_id = user.id
    username = user.username or user.full_name

    if query.data == 'join':
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await query.edit_message_text("⛔ Подпишись на наш канал, чтобы участвовать.")
                return
        except Exception:
            await query.edit_message_text("⚠️ Не удалось проверить подписку.")
            return

        async with aiosqlite.connect("lottery.db") as db:
            await db.execute(
                "INSERT OR IGNORE INTO participants (name, chat_id, joined_at) VALUES (?, ?, ?)",
                (username, chat_id, datetime.datetime.now().isoformat())
            )
            await db.commit()

        await query.edit_message_text(f"{username}, ты участвуешь в розыгрыше!")

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="🎉 Ты участвуешь в розыгрыше! Мы напишем тебе, если ты победишь."
            )
        except Forbidden:
            print(f"❌ Не могу отправить ЛС {username}")

    elif query.data == 'list':
        async with aiosqlite.connect("lottery.db") as db:
            async with db.execute("SELECT name FROM participants") as cursor:
                rows = await cursor.fetchall()
        if rows:
            names = "\n".join(name for (name,) in rows)
            await query.edit_message_text(f"👥 Участники:\n{names}")
        else:
            await query.edit_message_text("❗ Пока нет участников.")

    elif query.data == 'pick':
        if user.username != ADMIN_USERNAME:
            await query.edit_message_text("⛔ Только админ может выбрать победителя.")
            return

        async with aiosqlite.connect("lottery.db") as db:
            async with db.execute("SELECT name, chat_id FROM participants") as cursor:
                participants = await cursor.fetchall()

        if not participants:
            await query.edit_message_text("❗ Нет участников для розыгрыша.")
            return

        winner = random.choice(participants)
        name, winner_chat_id = winner

        async with aiosqlite.connect("lottery.db") as db:
            await db.execute(
                "INSERT INTO winners (name, method, picked_at) VALUES (?, ?, ?)",
                (name, 'general', datetime.datetime.now().isoformat())
            )
            await db.commit()

        # Отправляем всем участникам результат
        for _, chat in participants:
            try:
                await context.bot.send_message(chat_id=chat, text=f"🎉 Победитель: {name}!")
            except:
                pass

        await query.edit_message_text(f"🎉 Победитель: {name}!")

    elif query.data == 'reset':
        if user.username != ADMIN_USERNAME:
            await query.edit_message_text("⛔ Только админ может сбросить список.")
            return
        async with aiosqlite.connect("lottery.db") as db:
            await db.execute("DELETE FROM participants")
            await db.commit()
        await query.edit_message_text("✅ Список участников сброшен.")


async def main():
    await init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_button))

    print("🤖 Бот запущен!")
    await app.run_polling()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
