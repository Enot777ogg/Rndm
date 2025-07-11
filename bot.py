import os
import logging
import datetime
import random
import aiosqlite

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from telegram.error import Forbidden
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные окружения из .env

TOKEN = os.getenv("TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect("lottery.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS participants (
