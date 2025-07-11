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
        [InlineKeyboardButton("✅ Участвовать", callback_data="join")]_]()
