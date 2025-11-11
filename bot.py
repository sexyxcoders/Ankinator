from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID

# Plugins folder
plugins = dict(root="plugins")

# Initialize Pyrogram client
app = Client(
    "TNC",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=plugins
)

# Start bot
print("🚀 TNC Akinator Bot is starting...")

app.start()
print("✅ Bot started successfully!")

# Keep the bot running
idle()

# Stop bot
app.stop()
print("🛑 Bot stopped.")