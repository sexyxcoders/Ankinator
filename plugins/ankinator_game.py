from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import asyncio
from datetime import datetime
from config import MONGO_DB_URI
import motor.motor_asyncio

# ------------------------------
# MongoDB setup for stats
# ------------------------------
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# ------------------------------
# Active games tracker
# ------------------------------
active_games = {}  # user_id : session_id

# ------------------------------
# Update user stats
# ------------------------------
async def update_user_stats(user_id: int, won: bool):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    user = await stats.find_one({'user_id': user_id})
    if not user:
        user = {'user_id': user_id, 'total_games': 0, 'wins': 0, 'losses': 0, 'today_games': 0, 'today_date': today}

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
# Start Akinator Game
# ------------------------------
async def start_akinator_game(client: Client, message, user_id: int):
    if user_id in active_games:
        await message.reply("❌ You already have an active game! Use /stop to end it first.")
        return

    async with aiohttp.ClientSession() as session:
        try:
            # Start a new game session using free Akinator API
            async with session.get("https://tnc-akinator-api.vercel.app/start") as resp:
                data = await resp.json()
        except Exception as e:
            await message.reply(f"⚠️ Failed to start game: {e}")
            return

    session_id = data.get("session")
    active_games[user_id] = session_id

    # Send first question
    await message.reply(
        "🧞‍♂️ Game started! Think of a character, person, or object.\nI will try to guess it.\n\nYou can stop anytime using /stop.",
        reply_markup=InlineKeyboardMarkup([
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
    )

# ------------------------------
# Handle answer callbacks
# ------------------------------
@Client.on_callback_query(filters.regex(r"^ans_|stop_game"))
async def handle_answers(client, query):
    user_id = query.from_user.id
    if user_id not in active_games:
        return await query.answer("❌ You don't have an active game.", show_alert=True)

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

    session_id = active_games[user_id]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://tnc-akinator-api.vercel.app/answer?session={session_id}&answer={answer}") as resp:
                data = await resp.json()
        except Exception as e:
            del active_games[user_id]
            return await query.message.edit_text(f"⚠️ Error: {e}")

    progression = data.get("progression", 0)
    guess = data.get("guess")

    if guess or progression >= 80:
        del active_games[user_id]
        await update_user_stats(user_id, True)

        if guess:
            text = f"🤯 I think it's **{guess['name']}**!\n🧾 {guess['description']}\nWas I right?"
        else:
            text = "🤯 I made a guess!"

        await query.message.edit_text(text)
    else:
        # Ask next question
        await query.message.edit_text(
            "❓ " + data.get("question", "Next question?"),
            reply_markup=InlineKeyboardMarkup([
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
        )

# ------------------------------
# Commands
# ------------------------------
@Client.on_message(filters.command("play") & filters.private)
async def cmd_play(client, message):
    user_id = message.from_user.id
    await start_akinator_game(client, message, user_id)

@Client.on_message(filters.command("stop") & filters.private)
async def cmd_stop(client, message):
    user_id = message.from_user.id
    if user_id in active_games:
        del active_games[user_id]
        await message.reply("🛑 Game stopped. Use /play to start a new game.")
    else:
        await message.reply("❌ You don't have an active game.")