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

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# warnings structure:
# { chat_id: { user_id: warning_count } }
warnings = defaultdict(lambda: defaultdict(int))

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
            "• 3 Warning system (Group wise)\n"
            "• Auto mute after 3 warnings\n"
            "• Inline Unmute button\n\n"
            "Add me to your group and make me admin "
            "with Delete + Restrict permissions."
        )


# ================= GROUP MESSAGE FILTER =================
@bot.message_handler(content_types=['text'])
def check_abuse(message):

    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.first_name or "User"

    # 🔹 Skip admins
    member = bot.get_chat_member(chat_id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    text = normalize(message.text)

    for word in BAD_WORDS:
        if word in text:

            # Delete message
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                return

            # Increase warning group-wise
            warnings[chat_id][user_id] += 1
            current_warn = warnings[chat_id][user_id]

            mention = f"[{username}](tg://user?id={user_id})"

            # 🔥 MUTE CONDITION
            if current_warn >= MAX_WARNINGS:

                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user_id,
                        can_send_messages=False
                    )

                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton(
                            "🔓 Unmute",
                            callback_data=f"unmute:{chat_id}:{user_id}"
                        )
                    )

                    bot.send_message(
                        chat_id,
                        f"🚫 {mention} muted after {MAX_WARNINGS} warnings.",
                        reply_markup=markup
                    )

                except:
                    pass

                # Reset warning after mute
                warnings[chat_id][user_id] = 0

            else:
                bot.send_message(
                    chat_id,
                    f"⚠ {mention} Warning {current_warn}/{MAX_WARNINGS}"
                )

            break


# ================= UNMUTE BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("unmute:"))
def unmute_user(call):

    data = call.data.split(":")
    chat_id = int(data[1])
    user_id = int(data[2])

    # 🔹 Only admins can unmute
    member = bot.get_chat_member(chat_id, call.from_user.id)
    if member.status not in ["administrator", "creator"]:
        bot.answer_callback_query(
            call.id,
            "Only admins can unmute!",
            show_alert=True
        )
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
    bot.infinity_polling(skip_pending=True)
