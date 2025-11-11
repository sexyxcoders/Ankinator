# plugins/akinator_game.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiohttp
from datetime import datetime
from config import MONGO_DB_URI
import motor.motor_asyncio
from utils.image_fetch import fetch_image_url

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

active_games = {}  # user_id : dict with game data

def answer_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data="ans_yes"),
            InlineKeyboardButton("❌ No", callback_data="ans_no")
        ],
        [
            InlineKeyboardButton("🤔 Probably", callback_data="ans_probably"),
            InlineKeyboardButton("❓ Don't Know", callback_data="ans_dontknow")
        ],
        [InlineKeyboardButton("🛑 Stop", callback_data="stop_game")]
    ])

async def update_user_stats(user_id: int, won: bool):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    user = await stats.find_one({'user_id': user_id})
    if not user:
        user = {'user_id': user_id, 'total_games': 0, 'wins': 0, 'losses': 0,
                'today_games': 0, 'today_date': today}
    if user.get('today_date') != today:
        user['today_games'] = 0
        user['today_date'] = today
    user['total_games'] += 1
    user['today_games'] += 1
    if won:
        user['wins'] += 1
    else:
        user['losses'] += 1
    await stats.update_one({'user_id': user_id}, {'$set': user}, upsert=True)

@Client.on_message(filters.command("play"))
async def start_game(client: Client, message):
    user_id = message.from_user.id
    if user_id in active_games:
        return await message.reply_text("🎮 You already have an active game.")

    # Example URL for the aki‑api Node service (you must host or adjust)
    base_url = "https://your‑aki‑api‑url.com/api"  # change this to your endpoint
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/start?region=en") as resp:
                data = await resp.json()
        except Exception as e:
            return await message.reply_text(f"⚠️ Failed to start game: {e}")

    active_games[user_id] = {'session': data, 'base_url': base_url}
    await message.reply_text(f"❓ {data.get('question')}", reply_markup=answer_buttons())

@Client.on_callback_query(filters.regex(r"^(ans_|stop_game)"))
async def answer_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in active_games:
        return await query.answer("❌ No active game.", show_alert=True)

    game = active_games[user_id]
    if query.data == "stop_game":
        del active_games[user_id]
        await query.message.edit_text("🛑 Game stopped! Use /play to start again.")
        return

    map_ans = {"ans_yes": 0, "ans_no": 1, "ans_probably": 2, "ans_dontknow": 3}
    ans = map_ans.get(query.data, 3)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{game['base_url']}/answer",
                                   params={"session": game['session']['session'], "answer": ans}) as resp:
                data = await resp.json()
        except Exception as e:
            del active_games[user_id]
            return await query.message.edit_text(f"⚠️ Failed: {e}")

    if data.get('progression', 0) >= 90:
        # Guess
        try:
            guess = data.get('guess')
            del active_games[user_id]
            await update_user_stats(user_id, True)
            img_url = await fetch_image_url(guess.get('name', ''))
            text = f"🤯 I think it's **{guess.get('name','')}**!\n🧾 {guess.get('description','')}\nWas I right?"
            if img_url and img_url.startswith(("http://","https://")):
                try:
                    await query.message.reply_photo(img_url, caption=text)
                except:
                    await query.message.reply(text + "\n⚠️ Unable to send image.")
            else:
                await query.message.reply(text)
        except Exception as e:
            await query.message.reply(f"⚠️ Error retrieving result: {e}")
    else:
        await query.message.edit_text(f"❓ {data.get('question')}", reply_markup=answer_buttons())