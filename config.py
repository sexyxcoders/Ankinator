import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram API
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# Bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# MongoDB URI
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "")

# Owner/Admin ID
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Support chat and updates channel
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/TNCmeetups")
UPDATES_CHANNEL = os.getenv("UPDATES_CHANNEL", "https://t.me/TncNetwork")
