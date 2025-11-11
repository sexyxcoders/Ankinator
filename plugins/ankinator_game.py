# plugins/akinator_game.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from akinator.async_aki import Akinator
from datetime import datetime
from config import MONGO_DB_URI
import motor.motor_asyncio
import asyncio
from utils.image_fetch import fetch_image_url

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# Active games tracker
active_games = {}  # user_id : Akinator instance

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
# Start the Akinator game
# ------------------------------
async def start_akinator_game(client: Client, message, user_id: int):
    aki = Akinator()
    active_games[user_id] = aki
    q = await aki.start_game()
    await message.reply_text(
        f"❓ {q}",
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
# Handle answers via CallbackQuery
# ------------------------------
@Client.on_callback_query(filters.regex(r"^ans_|stop_game"))
async def answer_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in active_games:
        return await query.answer("❌ You don't have an active game.", show_alert=True)

    aki = active_games[user_id]

    if query.data == "stop_game":
        del active_games[user_id]
        await query.message.edit_text("🛑 Game stopped. Use /play to start a new game.")
        return

    # Map buttons to Akinator answers
    mapping = {
        "ans_yes": "yes",
        "ans_no": "no",
        "ans_probably": "probably",
        "ans_dontknow": "idk"
    }
    ans = mapping.get(query.data)

    try:
        q = await aki.answer(ans)
    except Exception as e:
        del active_games[user_id]
        await query.message.edit_text(f"⚠️ Game ended unexpectedly.\n\nError: {e}")
        return

    # If Akinator thinks it knows the answer
    if aki.progression >= 80:
        try:
            res = await aki.win()
            del active_games[user_id]

            # Update stats as win
            await update_user_stats(user_id, True)

            # Fetch dynamic image
            img_url = await fetch_image_url(res['name'])

            # Send result with image
            text = (
                f"🤯 I think it's **{res['name']}**!\n"
                f"🧾 {res['description']}\n"
                f"Was I right? (yes / no)"
            )
            if img_url:
                await query.message.reply_photo(img_url, caption=text)
            else:
                await query.message.reply(text)

        except Exception as e:
            del active_games[user_id]
            await query.message.edit_text(f"⚠️ Error retrieving result: {e}")
    else:
        # Ask next question
        await query.message.edit_text(
            f"❓ {q}",
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