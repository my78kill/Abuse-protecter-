import os
import asyncio
import threading
import re
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from collections import defaultdict

from badwords_hindi import HINDI_BAD_WORDS
from badwords_english import ENGLISH_BAD_WORDS

# ================= CONFIG =================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

MAX_WARNINGS = 3

BAD_WORDS = HINDI_BAD_WORDS + ENGLISH_BAD_WORDS

bot = Client("abuse-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
app = Flask(__name__)
warnings = defaultdict(int)

# ================= NORMALIZE =================
def normalize(text):
    text = text.lower()
    text = text.replace("@", "a").replace("0", "o").replace("$", "s")
    text = re.sub(r'[^a-zA-Zअ-ह]', '', text)
    return text

# ================= START COMMAND =================
@bot.on_message(filters.private & filters.command("start"))
async def start_handler(client, message):
    await message.reply(
        "👋 Hello!\n\n"
        "🤖 I am an Abuse Protection Bot.\n\n"
        "🔹 Features:\n"
        "• Detect Hindi & English abusive words\n"
        "• Auto delete abusive messages\n"
        "• 3 Warnings system\n"
        "• Auto mute after 3 warnings\n\n"
        "Add me to your group and make me admin with delete + restrict permissions."
    )

# ================= GROUP MESSAGE FILTER =================
@bot.on_message(filters.group & filters.text)
async def check_abuse(client, message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    text = normalize(message.text)

    for word in BAD_WORDS:
        if word in text:
            await message.delete()
            warnings[user_id] += 1

            if warnings[user_id] >= MAX_WARNINGS:
                await client.restrict_chat_member(
                    chat_id,
                    user_id,
                    ChatPermissions(can_send_messages=False)
                )
                await message.reply(
                    f"🚫 User muted after {MAX_WARNINGS} warnings."
                )
                warnings[user_id] = 0
            else:
                await message.reply(
                    f"⚠ Warning {warnings[user_id]}/{MAX_WARNINGS}\nAbusive language not allowed."
                )
            break

# ================= HEALTH CHECK =================
@app.route("/")
def home():
    return "Bot is running!"

# ================= RUN BOT + FLASK =================
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot.start())
    loop.run_forever()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
