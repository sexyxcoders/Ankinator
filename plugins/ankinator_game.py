# plugins/ankinator_game.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
import asyncio
import random
from utils.image_fetch import fetch_image_url  # your utility to fetch image from Google
from config import MONGO_DB_URI
import motor.motor_asyncio

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# Track active games
active_games = {}  # user_id : game_state


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
# Start fake Akinator game
# ------------------------------
async def start_akinator_game(client: Client, message, user_id: int):
    if user_id in active_games:
        await message.reply_text("❌ You already have an active game!")
        return

    # Fake game state
    game_state = {
        "questions": [
            "Is your character real?",
            "Is your character male?",
            "Is your character from a movie?",
            "Is your character animated?",
            "Is your character a superhero?"
        ],
        "current": 0,
        "progression": 0,
        "guess": {"name": "Iron Man", "description": "Marvel superhero played by Robert Downey Jr."}
    }
    active_games[user_id] = game_state

    q_text = game_state["questions"][game_state["current"]]
    await message.reply_text(
        f"🧞‍♂️ Game started! Think of a character, person, or object.\n\n❓ {q_text}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data="ans_yes"),
                InlineKeyboardButton("❌ No", callback_data="ans_no")
            ],
            [
                InlineKeyboardButton("🤔 Probably", callback_data="ans_probably"),
                InlineKeyboardButton("❓ Don't Know", callback_data="ans_dontknow")
            ],
            [
                InlineKeyboardButton("🛑 Stop", callback_data="stop_game")
            ]
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

    game_state = active_games[user_id]

    if query.data == "stop_game":
        del active_games[user_id]
        await query.message.edit_text("🛑 Game stopped. Use /play to start a new game.")
        return

    # Map buttons
    mapping = {
        "ans_yes": "yes",
        "ans_no": "no",
        "ans_probably": "probably",
        "ans_dontknow": "idk"
    }
    answer = mapping.get(query.data)

    # Fake progression logic
    game_state["current"] += 1
    game_state["progression"] += random.randint(15, 25)

    # Check if game finished
    if game_state["progression"] >= 80 or game_state["current"] >= len(game_state["questions"]):
        guess = game_state["guess"]
        del active_games[user_id]

        # Update stats as win
        await update_user_stats(user_id, True)

        # Fetch image
        img_url = await fetch_image_url(guess["name"])

        text = (
            f"🤯 I think it's **{guess['name']}**!\n"
            f"🧾 {guess['description']}\n"
            f"Was I right? (yes / no)"
        )

        if img_url:
            await query.message.reply_photo(img_url, caption=text)
        else:
            await query.message.reply(text)
    else:
        # Next question
        next_q = game_state["questions"][game_state["current"]]
        await query.message.edit_text(
            f"❓ {next_q}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yes", callback_data="ans_yes"),
                    InlineKeyboardButton("❌ No", callback_data="ans_no")
                ],
                [
                    InlineKeyboardButton("🤔 Probably", callback_data="ans_probably"),
                    InlineKeyboardButton("❓ Don't Know", callback_data="ans_dontknow")
                ],
                [
                    InlineKeyboardButton("🛑 Stop", callback_data="stop_game")
                ]
            ])
        )