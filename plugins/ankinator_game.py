from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
from config import MONGO_DB_URI
import motor.motor_asyncio
import asyncio
from utils.image_fetch import fetch_image_url  # optional for image

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# Track active games
active_games = {}  # user_id : game_state dict

# ------------------------------
# Update stats
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
# Fake questions
# ------------------------------
FAKE_QUESTIONS = [
    "Is your character real?",
    "Is your character from a movie?",
    "Is your character a superhero?",
    "Is your character male?",
    "Is your character animated?",
]

FAKE_GUESS = {
    "name": "Iron Man",
    "description": "Marvel superhero played by Robert Downey Jr."
}

# ------------------------------
# Start game
# ------------------------------
async def start_akinator_game(client: Client, message, user_id: int):
    active_games[user_id] = {"step": 0, "won": False}
    await message.reply_text(
        f"❓ {FAKE_QUESTIONS[0]}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="ans_yes"),
             InlineKeyboardButton("❌ No", callback_data="ans_no")],
            [InlineKeyboardButton("🛑 Stop", callback_data="stop_game")]
        ])
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

    game["step"] += 1
    progression = game["step"] * 20

    if progression >= 100:
        # Game ends, show guess
        del active_games[user_id]
        await update_user_stats(user_id, True)
        text = (
            f"🤯 I think it's **{FAKE_GUESS['name']}**!\n"
            f"🧾 {FAKE_GUESS['description']}\n"
            f"Was I right? (yes / no)"
        )
        img_url = await fetch_image_url(FAKE_GUESS['name'])
        if img_url:
            await query.message.reply_photo(img_url, caption=text)
        else:
            await query.message.reply(text)
    else:
        # Next fake question
        next_q = FAKE_QUESTIONS[min(game["step"], len(FAKE_QUESTIONS)-1)]
        await query.message.edit_text(
            f"❓ {next_q}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yes", callback_data="ans_yes"),
                 InlineKeyboardButton("❌ No", callback_data="ans_no")],
                [InlineKeyboardButton("🛑 Stop", callback_data="stop_game")]
            ])
        )