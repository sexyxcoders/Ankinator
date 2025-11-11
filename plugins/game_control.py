from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
import asyncio

# Dictionary to track active games per user
active_games = {}  # user_id : True/False

# ------------------------------
# /play command
# ------------------------------
@Client.on_message(filters.command("play"))
async def play_game(client: Client, message: Message):
    user_id = message.from_user.id
    if active_games.get(user_id):
        return await message.reply("🎮 You already have an active game! Use /stop to end it.")

    active_games[user_id] = True
    await message.reply(
        "🧞‍♂️ Game started! Think of a character, person, or object.\n"
        "I will try to guess it.\n\n"
        "You can stop anytime using /stop."
    )

    # Call the akinator game function from akinator_game.py
    # For example, assuming you have a function: start_akinator_game(client, message)
    try:
        from plugins.akinator_game import start_akinator_game
        await start_akinator_game(client, message, user_id)
    except ImportError:
        await message.reply("⚠️ Akinator game plugin not found!")

# ------------------------------
# /stop command
# ------------------------------
@Client.on_message(filters.command("stop"))
async def stop_game(client: Client, message: Message):
    user_id = message.from_user.id
    if not active_games.get(user_id):
        return await message.reply("❌ You don't have an active game to stop.")

    active_games[user_id] = False
    await message.reply("🛑 Your game has been stopped. You can start a new game anytime using /play.")
