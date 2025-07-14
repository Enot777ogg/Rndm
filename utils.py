import random
from telegram import User
from database import get_participants

async def choose_random_winner(bot, cid):
    participants = get_participants(cid)
    if not participants:
        return None
    winner_id = random.choice(participants)
    return await bot.get_chat(winner_id)

async def notify_all(bot, cid, winner: User):
    users = get_participants(cid)
    for uid in users:
        try:
            await bot.send_message(uid, f"🏆 Победитель конкурса {cid}: @{winner.username or winner.first_name}")
        except:
            continue
