from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from config import SUPPORT_CHAT, UPDATES_CHANNEL

# You can add multiple start images
START_IMAGES = [
    "https://telegra.ph/file/ee8b25b05d54cbe13438a.jpg",
    "https://telegra.ph/file/1f0ad8fbe1fdce07a9e38.jpg"
]

@Client.on_message(filters.command(["start", "help"]))
async def start(client, message):
    start_img = random.choice(START_IMAGES)
    name = message.from_user.first_name

    caption = (
        f"👋 **Hey {name}!**\n\n"
        "🎮 Welcome to **TNC Akinator Bot** 🧞‍♂️\n\n"
        "Think of any character, person, or object — I'll try to guess it!\n\n"
        "Tap Play Now to start 👇"
    )

    await message.reply_photo(
        photo=start_img,
        caption=caption,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧩 Play Now", callback_data="start_akinator")],
            [
                InlineKeyboardButton("💬 Support Chat", url=SUPPORT_CHAT),
                InlineKeyboardButton("📢 Updates Channel", url=UPDATES_CHANNEL),
            ]
        ])
    )
