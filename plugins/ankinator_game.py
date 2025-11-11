import os
import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
from config import MONGO_DB_URI
import motor.motor_asyncio
from utils.image_fetch import fetch_image_url

# ------------------------------
# Environment
# ------------------------------
AKI_API_KEY = os.getenv("AKINATOR_API_KEY")
AKI_API_HOST = os.getenv("AKINATOR_API_HOST")
HEADERS = {
    "X-RapidAPI-Key": AKI_API_KEY,
    "X-RapidAPI-Host": AKI_API_HOST
}

# ------------------------------
# MongoDB setup
# ------------------------------
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# ------------------------------
# Active games tracker
# ------------------------------
active_games = {}  # user_id : {game_id, step, session_data}

# ------------------------------
# Helper: Update stats
# ------------------------------
async def update_user_stats(user_id: int, won: bool):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    user = await stats.find_one({'user_id': user_id})
    if not user:
        user = {
            'user_id': user_id,
            'total_games': 0,
            'wins': 0,
            'losses': 0,
            'today_games': 0,
            'today_date': today,
        }
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

# ------------------------------
# Helper: Inline buttons
# ------------------------------
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

# ------------------------------
# Start game
# ------------------------------
@Client.on_message(filters.command("play"))
async def start_akinator_game(client: Client, message):
    user_id = message.from_user.id
    if user_id in active_games:
        return await message.reply_text("❌ You already have an active game.")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://{AKI_API_HOST}/start", headers=HEADERS) as resp:
                data = await resp.json()
        except Exception as e:
            return await message.reply_text(f"⚠️ Failed to start game: {e}")

    # Save active game
    active_games[user_id] = {
        "game_id": data["game_id"],
        "step": data["step"],
        "session_data": data
    }

    await message.reply_text(
        f"❓ {data['question']}",
        reply_markup=answer_buttons()
    )

# ------------------------------
# Handle answers
# ------------------------------
@Client.on_callback_query(filters.regex(r"^ans_|stop_game"))
async def answer_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in active_games:
        return await query.answer("❌ You don't have an active game.", show_alert=True)

    game = active_games[user_id]

    if query.data == "stop_game":
        del active_games[user_id]
        await query.message.edit_text("🛑 Game stopped. Use /play to start a new game.")
        return

    ans_map = {
        "ans_yes": 0,
        "ans_no": 1,
        "ans_probably": 2,
        "ans_dontknow": 3
    }
    ans_value = ans_map.get(query.data)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"https://{AKI_API_HOST}/answer",
                headers=HEADERS,
                params={"game_id": game["game_id"], "answer": ans_value}
            ) as resp:
                data = await resp.json()
        except Exception as e:
            del active_games[user_id]
            return await query.message.edit_text(f"⚠️ Failed to answer: {e}")

    # Update step
    game["step"] = data["step"]

    # Check progression
    if data.get("progression", 0) >= 90:
        try:
            result = data["result"]
            del active_games[user_id]
            await update_user_stats(user_id, True)

            # Fetch image safely
            img_url = await fetch_image_url(result["name"])
            text = (
                f"🤯 I think it's **{result['name']}**!\n"
                f"🧾 {result['description']}\n"
                f"Was I right? (yes / no)"
            )

            if img_url and img_url.startswith(("http://", "https://")):
                try:
                    await query.message.reply_photo(img_url, caption=text)
                except:
                    await query.message.reply(text + "\n⚠️ Could not send image.")
            else:
                await query.message.reply(text)

        except Exception as e:
            del active_games[user_id]
            await query.message.edit_text(f"⚠️ Failed to retrieve result: {e}")
    else:
        await query.message.edit_text(
            f"❓ {data['question']}",
            reply_markup=answer_buttons()
        )