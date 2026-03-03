import os
import re
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from badwords_hindi import HINDI_BAD_WORDS
from badwords_english import ENGLISH_BAD_WORDS

api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

app = Flask(__name__)

bot = Client(
    "abusebot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

WARN_LIMIT = 3
warnings = {}

# 🔥 Normalize Roman text (masked detection)
def normalize_roman(text):
    text = text.lower()

    replacements = {
        "@": "a",
        "4": "a",
        "0": "o",
        "$": "s",
        "1": "i",
        "!": "i",
        "3": "e",
        "7": "t"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r"[.\s_\-]", "", text)

    return text


# 🔥 Abuse checker
def contains_abuse(original_text):

    roman_text = normalize_roman(original_text)
    lower_text = original_text.lower()

    # Roman Hindi check
    for word in HINDI_BAD_WORDS:
        if word in roman_text:
            return True

    # English check
    for word in ENGLISH_BAD_WORDS:
        if word in roman_text:
            return True

    # Devanagari check (direct match)
    for word in HINDI_BAD_WORDS:
        if word in lower_text:
            return True

    return False


@bot.on_message(filters.text & filters.group)
async def check_abuse(client, message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    member = await client.get_chat_member(chat_id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    if contains_abuse(message.text):

        await message.delete()

        if chat_id not in warnings:
            warnings[chat_id] = {}

        if user_id not in warnings[chat_id]:
            warnings[chat_id][user_id] = 0

        warnings[chat_id][user_id] += 1
        warn_count = warnings[chat_id][user_id]

        await message.reply_text(
            f"⚠ Warning {warn_count}/{WARN_LIMIT}"
        )

        if warn_count >= WARN_LIMIT:
            await client.restrict_chat_member(
                chat_id,
                user_id,
                ChatPermissions()
            )

            await message.reply_text("🔇 User muted (3 warnings reached)")
            warnings[chat_id][user_id] = 0


@app.route("/")
def home():
    return "Abuse Protection Bot Running!"

if __name__ == "__main__":
    bot.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)