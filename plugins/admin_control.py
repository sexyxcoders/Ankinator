from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, MONGO_DB_URI
import motor.motor_asyncio
import asyncio

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
users_col = db["user_stats"]  # same collection where user_id is stored

# Admin broadcast command
@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client: Client, message: Message):
    if len(message.command) < 2 and not message.reply_to_message:
        return await message.reply(
            "❌ Usage:\n/broadcast Your message here\n\nOr reply to a message with /broadcast"
        )

    # Determine message to send
    if message.reply_to_message:
        text_to_send = message.reply_to_message.text or message.reply_to_message.caption
    else:
        text_to_send = message.text.split(" ", 1)[1]

    # Fetch all user IDs
    cursor = users_col.find({})
    user_ids = [user['user_id'] async for user in cursor]

    sent_count = 0
    failed_count = 0

    for uid in user_ids:
        try:
            await client.send_message(uid, text_to_send)
            sent_count += 1
            await asyncio.sleep(0.1)  # small delay to avoid flooding
        except Exception:
            failed_count += 1

    await message.reply(
        f"✅ Broadcast completed!\n\n"
        f"Sent: {sent_count}\nFailed: {failed_count}"
    )

# Prevent non-admins from using broadcast
@Client.on_message(filters.command("broadcast") & ~filters.user(OWNER_ID))
async def not_admin(client: Client, message: Message):
    await message.reply("❌ You are not allowed to use this command.")