import logging
import sqlite3
import random
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, ParseMode
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = "bytravka"

(
    CREATE_DESC,
    CREATE_PHOTO,
    CREATE_DATETIME,
    CREATE_GROUP,
    CONFIRMATION
) = range(5)

conn = sqlite3.connect('rndm_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS contests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    photo_file_id TEXT,
    post_datetime TEXT NOT NULL,
    group_chat_id TEXT NOT NULL
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS participants (
    contest_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    PRIMARY KEY (contest_id, user_id)
)
''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Список конкурсов", callback_data='list_contests')],
        [InlineKeyboardButton("✅ Участвовать", callback_data='join')],
    ]
    if update.effective_user.username == ADMIN_USERNAME:
        keyboard.append([InlineKeyboardButton("➕ Создать конкурс", callback_data='create_contest')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать в Rndm Bot!\nВыберите действие:", reply_markup=reply_markup)

async def list_contests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cursor.execute("SELECT id, description, post_datetime FROM contests ORDER BY id DESC")
    contests = cursor.fetchall()
    if not contests:
        await query.edit_message_text("Пока нет активных конкурсов.")
        return
    text = "📋 Активные конкурсы:\n\n"
    for c in contests:
        cid, desc, dt = c
        text += f"ID: {cid}\nОписание: {desc}\nДата публикации: {dt}\n\n"
    await query.edit_message_text(text)

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    cursor.execute("SELECT id, description FROM contests ORDER BY id DESC")
    contests = cursor.fetchall()
    if not contests:
        await query.edit_message_text("Пока нет конкурсов для участия.")
        return
    keyboard = [
        [InlineKeyboardButton(f"{c[1]} (ID: {c[0]})", callback_data=f"join_{c[0]}")]
        for c in contests
    ]
    await query.edit_message_text("Выберите конкурс, в котором хотите участвовать:", reply_markup=InlineKeyboardMarkup(keyboard))

async def join_contest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    contest_id = int(query.data.split('_')[1])
    cursor.execute("SELECT 1 FROM contests WHERE id=?", (contest_id,))
    if not cursor.fetchone():
        await query.edit_message_text("Такого конкурса нет.")
        return
    cursor.execute("SELECT 1 FROM participants WHERE contest_id=? AND user_id=?", (contest_id, user.id))
    if cursor.fetchone():
        await query.edit_message_text("Вы уже участвуете в этом конкурсе.")
        return
    cursor.execute("INSERT INTO participants (contest_id, user_id, username) VALUES (?, ?, ?)", (contest_id, user.id, user.username or ""))
    conn.commit()
    await query.edit_message_text("Вы успешно зарегистрировались в конкурсе!")

async def create_contest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.callback_query.from_user
    if user.username != ADMIN_USERNAME:
        await update.callback_query.answer("⛔ Только админ может создавать конкурсы", show_alert=True)
        return
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Введите описание конкурса:")
    return CREATE_DESC

async def create_contest_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contest_desc'] = update.message.text
    await update.message.reply_text("Отправьте картинку для конкурса (или напишите /skip, чтобы пропустить):")
    return CREATE_PHOTO

async def create_contest_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo
    if not photo:
        await update.message.reply_text("Пожалуйста, отправьте картинку или /skip:")
        return CREATE_PHOTO
    context.user_data['contest_photo'] = photo[-1].file_id
    await update.message.reply_text("Введите дату и время публикации конкурса в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-07-15 18:30):")
    return CREATE_DATETIME

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contest_photo'] = None
    await update.message.reply_text("Введите дату и время публикации конкурса в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-07-15 18:30):")
    return CREATE_DATETIME

async def create_contest_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        context.user_data['contest_datetime'] = dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Попробуйте ещё раз:")
        return CREATE_DATETIME
    await update.message.reply_text("Введите ID группы, в которую нужно выложить пост (например, -1001234567890):")
    return CREATE_GROUP

async def create_contest_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_id = update.message.text.strip()
    if not group_id.startswith("-100") or not group_id[1:].isdigit():
        await update.message.reply_text("Неверный формат ID группы. Попробуйте ещё раз:")
        return CREATE_GROUP
    context.user_data['contest_group'] = group_id
    desc = context.user_data['contest_desc']
    photo = context.user_data['contest_photo']
    dt = context.user_data['contest_datetime']
    group = context.user_data['contest_group']
    msg = (f"Проверьте данные:\n\n"
           f"Описание: {desc}\n"
           f"Дата публикации: {dt}\n"
           f"Группа: {group}\n"
           f"Картинка: {'есть' if photo else 'нет'}\n\n"
           f"Подтвердите /confirm или отмените /cancel")
    await update.message.reply_text(msg)
    return CONFIRMATION

async def confirm_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = context.user_data['contest_desc']
    photo = context.user_data['contest_photo']
    dt = context.user_data['contest_datetime']
    group = context.user_data['contest_group']
    cursor.execute(
        "INSERT INTO contests (description, photo_file_id, post_datetime, group_chat_id) VALUES (?, ?, ?, ?)",
        (desc, photo, dt, group)
    )
    conn.commit()
    await update.message.reply_text("✅ Конкурс создан!")
    return ConversationHandler.END

async def cancel_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Создание конкурса отменено.")
    return ConversationHandler.END

# --- Выбор победителя (администратор) ---

async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text("⛔ Только админ может выбирать победителя.")
        return
    if not context.args:
        await update.message.reply_text("❗ Использование: /pickwinner <id_конкурса>")
        return
    try:
        contest_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❗ Неверный ID конкурса.")
        return

    # Получаем всех участников конкурса
    cursor.execute("SELECT user_id, username FROM participants WHERE contest_id=?", (contest_id,))
    participants = cursor.fetchall()

    if not participants:
        await update.message.reply_text("❗ В этом конкурсе нет участников.")
        return

    # Выбираем случайного победителя
    winner = random.choice(participants)
    winner_id, winner_username = winner

    # Отправляем сообщение о победителе в чат админа
    await update.message.reply_text(
        f"🏆 Победитель конкурса {contest_id}:\n@{winner_username} (id: {winner_id})"
    )

    # Уведомляем всех участников
    for user_id, username in participants:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(f"🎉 Победитель конкурса #{contest_id} — @{winner_username}!\n"
                      f"Поздравляем! Спасибо за участие.")
            )
        except Exception:
            pass

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "list_contests":
        await list_contests(update, context)
    elif data == "join":
        await join(update, context)
    elif data.startswith("join_"):
        await join_contest_callback(update, context)
    elif data == "create_contest":
        await create_contest_start(update, context)
    else:
        await query.answer("Неизвестная команда")

def main():
    TOKEN = "ВАШ_ТОКЕН_ЗДЕСЬ"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pickwinner", pick_winner
