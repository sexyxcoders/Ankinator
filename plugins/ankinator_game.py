from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import aiohttp
import asyncio

# Active games tracker
active_games = {}  # user_id: session_id

API_URL = "http://127.0.0.1:3000"  # Local Akinator API

# ------------------------------
# Start game command
# ------------------------------
@Client.on_message(filters.command("play") & filters.private)
async def start_game(client: Client, message):
    user_id = message.from_user.id
    if user_id in active_games:
        await message.reply("❌ You already have an active game!")
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/start") as resp:
                data = await resp.json()
        except Exception as e:
            await message.reply(f"⚠️ Failed to start game: {e}")
            return

    session_id = data.get("session")
    question = data.get("question", "Think of a character...")
    active_games[user_id] = session_id

    await message.reply(
        f"🧞‍♂️ Game started! {question}\n\nYou can stop anytime using /stop.",
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
# Handle answers
# ------------------------------
@Client.on_callback_query(filters.regex(r"^ans_|stop_game"))
async def handle_answer(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if user_id not in active_games:
        return await query.answer("❌ You don't have an active game.", show_alert=True)

    if query.data == "stop_game":
        del active_games[user_id]
        await query.message.edit_text("🛑 Game stopped. Use /play to start a new game.")
        return

    answer_map = {
        "ans_yes": "yes",
        "ans_no": "no",
        "ans_probably": "probably",
        "ans_dontknow": "idk"
    }
    answer = answer_map.get(query.data)
    session_id = active_games[user_id]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_URL}/answer", params={"session": session_id, "answer": answer}) as resp:
                data = await resp.json()
        except Exception as e:
            del active_games[user_id]
            await query.message.edit_text(f"⚠️ Error: {e}")
            return

    progression = data.get("progression", 0)
    guess = data.get("guess")

    if progression >= 80 and guess:
        del active_games[user_id]
        text = f"🤯 I think it's **{guess['name']}**!\n🧾 {guess.get('description','')}"
        await query.message.edit_text(text)
    else:
        question = data.get("question", "Next question?")
        await query.message.edit_text(
            f"❓ {question}",
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