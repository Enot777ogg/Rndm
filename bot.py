import logging
import asyncio
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, ConversationHandler, MessageHandler, filters
)
from datetime import datetime
import os
import random

# Конфигурация
BOT_TOKEN = os.getenv(BOT_TOKEN="7906093019:AAH_Fme_DwCq9okVAUNZA17OlZwgBfp0NY4")
ADMIN_USERNAME = "@bytravka"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Память
contests = {}         # contest_id: {title, description, photo_id, datetime, group, creator}
participants = {}     # contest_id: [user_ids]

# Состояния
TITLE, DESCRIPTION, PHOTO, DATETIME, GROUP = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎉 Участвовать в конкурсе", callback_data="join_contest")],
        [InlineKeyboardButton("🆕 Создать конкурс", callback_data="create_contest")],
    ]
    await update.message.reply_text("Добро пожаловать в RndmBot!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "join_contest":
        if not contests:
            await query.message.reply_text("Нет активных конкурсов.")
            return
        for cid, contest in contests.items():
            text = f"🎁 {contest['title']}\n📅 {contest['datetime']}\n📍 {contest['group']}"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Участвовать", callback_data=f"join_{cid}")]
            ])
            await query.message.reply_photo(photo=contest["photo_id"], caption=text, reply_markup=keyboard)
    elif data.startswith("join_"):
        cid = data.split("_")[1]
        uid = query.from_user.id
        if cid not in participants:
            participants[cid] = []
        if uid not in participants[cid]:
            participants[cid].append(uid)
            await context.bot.send_message(chat_id=uid, text="✅ Вы участвуете в конкурсе!")
    elif data == "create_contest":
        await query.message.reply_text("Введите название конкурса:")
        return TITLE

async def title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Введите описание конкурса:")
    return DESCRIPTION

async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("Пришлите изображение:")
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_id"] = update.message.photo[-1].file_id
    await update.message.reply_text("Введите дату и время (ГГГГ-ММ-ДД ЧЧ:ММ):")
    return DATETIME

async def datetime_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["datetime"] = update.message.text
    await update.message.reply_text("Укажите название группы:")
    return GROUP

async def group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = update.message.text
    cid = str(len(contests) + 1)
    contests[cid] = {
        "title": context.user_data["title"],
        "description": context.user_data["description"],
        "photo_id": context.user_data["photo_id"],
        "datetime": context.user_data["datetime"],
        "group": group,
        "creator": update.message.from_user.username,
    }
    await update.message.reply_text(f"✅ Конкурс создан! ID: {cid}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Создание отменено.")
    return ConversationHandler.END

async def choose_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    args = context.args
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("⛔ Доступ только для администратора.")
        return
    if not args:
        await update.message.reply_text("Укажите ID конкурса: /winner <id>")
        return
    cid = args[0]
    if cid not in participants or not participants[cid]:
        await update.message.reply_text("❗ Нет участников.")
        return
    winner_id = random.choice(participants[cid])
    winner = await context.bot.get_chat(winner_id)
    await update.message.reply_text(f"🏆 Победитель: @{winner.username or winner.first_name}")
    for uid in participants[cid]:
        try:
            await context.bot.send_message(chat_id=uid, text=f"🎉 Конкурс {cid} завершён. Победитель: @{winner.username or winner.first_name}")
        except:
            continue

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, datetime_input)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, group_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("winner", choose_winner))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
