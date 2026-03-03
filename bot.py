import telebot
import threading
import re
from collections import defaultdict
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import main
from badwords_hindi import HINDI_BAD_WORDS
from badwords_english import ENGLISH_BAD_WORDS

# ================= CONFIG =================
BOT_TOKEN = "8661390665:AAEvNvlvNBHi8j6n4rwtO3yVqVl-D63CEOo"
MAX_WARNINGS = 3

bot = telebot.TeleBot(BOT_TOKEN)
warnings = defaultdict(int)

BAD_WORDS = HINDI_BAD_WORDS + ENGLISH_BAD_WORDS

# ================= NORMALIZE =================
def normalize(text):
    text = text.lower()
    text = text.replace("@", "a").replace("0", "o").replace("$", "s")
    text = re.sub(r'[^a-zA-Zअ-ह]', '', text)
    return text

# ================= START COMMAND =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == "private":
        bot.reply_to(
            message,
            "👋 Hello!\n\n"
            "🤖 I am an Abuse Protection Bot.\n\n"
            "🔹 Features:\n"
            "• Detect Hindi & English abusive words\n"
            "• Auto delete abusive messages\n"
            "• 3 Warning system\n"
            "• Auto mute after 3 warnings\n"
            "• Inline Unmute button\n\n"
            "Add me to your group and make me admin "
            "with delete + restrict permissions."
        )

# ================= GROUP MESSAGE FILTER =================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def check_abuse(message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.first_name

    text = normalize(message.text)

    for word in BAD_WORDS:
        if word in text:
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                return

            warnings[user_id] += 1

            mention = f"[{username}](tg://user?id={user_id})"

            if warnings[user_id] >= MAX_WARNINGS:
                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user_id,
                        can_send_messages=False
                    )

                    # Unmute Button
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton(
                            "🔓 Unmute",
                            callback_data=f"unmute_{user_id}"
                        )
                    )

                    bot.send_message(
                        chat_id,
                        f"🚫 {mention} muted after {MAX_WARNINGS} warnings.",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )

                except:
                    pass

                warnings[user_id] = 0

            else:
                bot.send_message(
                    chat_id,
                    f"⚠ {mention} Warning {warnings[user_id]}/{MAX_WARNINGS}\nAbusive language not allowed.",
                    parse_mode="Markdown"
                )
            break

# ================= UNMUTE BUTTON HANDLER =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("unmute_"))
def unmute_user(call):
    chat_id = call.message.chat.id
    user_id = int(call.data.split("_")[1])

    # Check if button clicker is admin
    member = bot.get_chat_member(chat_id, call.from_user.id)
    if member.status not in ["administrator", "creator"]:
        bot.answer_callback_query(call.id, "Only admins can unmute!", show_alert=True)
        return

    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            can_send_messages=True
        )

        bot.edit_message_text(
            "✅ User unmuted by admin.",
            chat_id,
            call.message.message_id
        )

    except:
        pass

# ================= RUN FLASK + BOT =================
if __name__ == "__main__":
    threading.Thread(
        target=main.app.run,
        kwargs={"host": "0.0.0.0", "port": 10000}
    ).start()

    print("Bot is running...")
    bot.infinity_polling()
