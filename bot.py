import telebot
import threading
import re
from collections import defaultdict

import main
from badwords_hindi import HINDI_BAD_WORDS
from badwords_english import ENGLISH_BAD_WORDS

# ================= CONFIG =================
BOT_TOKEN = "8661390665:AAEvNvlvNBHi8j6n4rwtO3yVqVl-D63CEOo"  # Replace with your token
MAX_WARNINGS = 3

bot = telebot.TeleBot(BOT_TOKEN)
warnings = defaultdict(int)

BAD_WORDS = HINDI_BAD_WORDS + ENGLISH_BAD_WORDS

# ================= NORMALIZE FUNCTION =================
def normalize(text):
    text = text.lower()
    text = text.replace("@", "a").replace("0", "o").replace("$", "s")
    text = re.sub(r'[^a-zA-Zअ-ह]', '', text)
    return text

# ================= START COMMAND (DM) =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == "private":
        bot.reply_to(
            message,
            "Hello!\n\n"
            "I am an Abuse Protection Bot.\n\n"
            "Features:\n"
            "• Detect Hindi & English abusive words\n"
            "• Auto delete abusive messages\n"
            "• 3 Warning system\n"
            "• Auto mute after 3 warnings\n\n"
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

    text = normalize(message.text)

    for word in BAD_WORDS:
        if word in text:
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                return

            warnings[user_id] += 1

            if warnings[user_id] >= MAX_WARNINGS:
                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user_id,
                        can_send_messages=False
                    )
                    bot.send_message(
                        chat_id,
                        f"User muted after {MAX_WARNINGS} warnings."
                    )
                except:
                    pass
                warnings[user_id] = 0
            else:
                bot.send_message(
                    chat_id,
                    f"Warning {warnings[user_id]}/{MAX_WARNINGS}\nAbusive language not allowed."
                )
            break

# ================= RUN FLASK + BOT =================
if __name__ == "__main__":
    threading.Thread(
        target=main.app.run,
        kwargs={"host": "0.0.0.0", "port": 10000}
    ).start()

    print("Bot is running...")
    bot.infinity_polling()