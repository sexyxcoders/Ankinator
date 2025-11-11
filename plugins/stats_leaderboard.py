from pyrogram import Client, filters
from pyrogram.types import Message
import motor.motor_asyncio
from datetime import datetime
from config import MONGO_DB_URI

# MongoDB setup
mongo = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["tnc_db"]
stats = db["user_stats"]

# ------------------------------
# Update user stats after each game
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
    # Reset today's games if date changed
    if user.get('today_date') != today:
        user['today_games'] = 0
        user['today_date'] = today

    # Update stats
    user['total_games'] += 1
    user['today_games'] += 1
    if won:
        user['wins'] += 1
    else:
        user['losses'] += 1

    await stats.update_one({'user_id': user_id}, {'$set': user}, upsert=True)

# ------------------------------
# Helper to mention a user
# ------------------------------
async def get_mention(app, user_id):
    try:
        u = await app.get_users(user_id)
        return u.mention
    except:
        return f'`{user_id}`'

# ------------------------------
# /stats command
# ------------------------------
@Client.on_message(filters.command('stats'))
async def player_stats(app: Client, message: Message):
    user_id = message.from_user.id
    user = await stats.find_one({'user_id': user_id})
    if not user:
        return await message.reply('📊 You haven\'t played any games yet! Use /play to start.')

    await message.reply(
        f"📊 **Your Akinator Stats**\n\n"
        f"👤 **Player:** {message.from_user.mention}\n"
        f"🎮 **Games Played:** `{user['total_games']}`\n"
        f"🏆 **Wins:** `{user['wins']}`\n"
        f"💀 **Losses:** `{user['losses']}`\n"
        f"🎯 **Today's Games:** `{user['today_games']}`\n"
    )

# ------------------------------
# /toptoday command
# ------------------------------
@Client.on_message(filters.command('toptoday'))
async def top_today(app: Client, message: Message):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    cursor = stats.find({'today_date': today}).sort('today_games', -1).limit(10)
    text = '🏅 **Top Players Today**\n\n'
    i = 1
    async for u in cursor:
        name = await get_mention(app, u['user_id'])
        text += f"#{i} — {name} | 🎯 `{u['today_games']}` games\n"
        i += 1
    if i == 1:
        text += 'No games played today yet!'
    await message.reply(text)

# ------------------------------
# /topoverall command
# ------------------------------
@Client.on_message(filters.command('topoverall'))
async def top_overall(app: Client, message: Message):
    cursor = stats.find({}).sort('total_games', -1).limit(10)
    text = '🏆 **All-Time Top Players**\n\n'
    i = 1
    async for u in cursor:
        name = await get_mention(app, u['user_id'])
        text += f"#{i} — {name} | 🎮 `{u['total_games']}` games\n"
        i += 1
    if i == 1:
        text += 'No players found!'
    await message.reply(text)

# ------------------------------
# /top command (combined)
# ------------------------------
@Client.on_message(filters.command('top'))
async def combined_top(app: Client, message: Message):
    today = datetime.utcnow().strftime('%Y-%m-%d')
    t_today = stats.find({'today_date': today}).sort('today_games', -1).limit(3)
    t_all = stats.find({}).sort('total_games', -1).limit(3)
    text = '⚡ **Leaderboard Summary**\n\n'
    text += "🏅 **Today's Top 3:**\n"
    i = 1
    async for u in t_today:
        name = await get_mention(app, u['user_id'])
        text += f"#{i} — {name} | 🎯 `{u['today_games']}` games\n"
        i += 1
    text += "\n🏆 **All-Time Top 3:**\n"
    i = 1
    async for u in t_all:
        name = await get_mention(app, u['user_id'])
        text += f"#{i} — {name} | 🎮 `{u['total_games']}` games\n"
        i += 1
    await message.reply(text)