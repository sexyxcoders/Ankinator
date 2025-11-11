# bot.py
import os
from pyrogram import Client, idle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

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