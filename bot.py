import telebot
import threading
import re
from collections import defaultdict
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
BOT_TOKEN = "8661390665:AAEvNvlvNBHi8j6n4rwtO3yVqVl-D63CEOo"
MAX_WARNINGS = 3
ABUSE_FILE = "abuse.txt"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= DATA STRUCTURES =================
# { chat_id: { user_id: warning_count } }
warnings = defaultdict(lambda: defaultdict(int))
# { chat_id: set(user_ids) } -> authorized users bypass abuse filter
authorized_users = defaultdict(set)

# ================= WARNING MESSAGES =================
WARNING_MESSAGES = {
    1: "⚠️ {mention}, please keep it respectful!",
    2: "⛔ {mention}, second warning!",
    3: "🚦 {mention}, final warning!",
    4: "🛑 {mention}, muted next!",
    5: "🚫 {mention}, you will be removed!",
    6: "🔥 {mention}, banned!"
}

# ================= LOAD ABUSIVE WORDS =================
def load_abusive_words():
    if not ABUSE_FILE:
        return []
    try:
        with open(ABUSE_FILE, "r", encoding="utf-8") as f:
            return [w.strip().lower() for w in f if w.strip()]
    except FileNotFoundError:
        return []

ABUSIVE_WORDS = load_abusive_words()

# ================= NORMALIZE MESSAGE =================
def normalize(text):
    text = text.lower()
    text = text.replace("@", "a").replace("0", "o").replace("$", "s")
    text = re.sub(r'[^a-zA-Zअ-ह]', '', text)
    return text

# ================= START COMMAND / DM =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == "private":
        bot.reply_to(
            message,
            "👋 Welcome!\n\n"
            "# 🤖 Telegram Abuse Filter Bot 🚀\n\n"
            "A **powerful** Telegram bot that **automatically deletes abusive messages** "
            "and warns users based on violations. Built for **secure and safe group management**!\n\n"
            "---\n"
            "## ⚡ Features\n"
            "✅ **Auto-delete** abusive messages ❌\n"
            "✅ **Warn users** with increasing severity ⚠️\n"
            "✅ **Admin-only authentication** to whitelist users 🔑\n"
            "✅ **Multi-group support** 📌\n"
            "✅ **Customizable warning messages** 💬\n\n"
            "Add me to your group and make me admin with Delete + Restrict permissions."
        )

# ================= AUTH / UNAUTH =================
@bot.message_handler(commands=['auth'])
def auth_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a user to authorize.")
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    # Check admin
    member = bot.get_chat_member(chat_id, admin_id)
    if member.status not in ["administrator", "creator"]:
        bot.reply_to(message, "🚫 Only admins can authorize.")
        return

    authorized_users[chat_id].add(target_id)
    bot.reply_to(message, f"✅ [{message.reply_to_message.from_user.first_name}](tg://user?id={target_id}) authorized. Abuse bypass active.", parse_mode="Markdown")

@bot.message_handler(commands=['unauth'])
def unauth_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a user to unauthorize.")
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id
    target_id = message.reply_to_message.from_user.id

    # Check admin
    member = bot.get_chat_member(chat_id, admin_id)
    if member.status not in ["administrator", "creator"]:
        bot.reply_to(message, "🚫 Only admins can unauthorize.")
        return

    authorized_users[chat_id].discard(target_id)
    bot.reply_to(message, f"❌ [{message.reply_to_message.from_user.first_name}](tg://user?id={target_id}) unauthorized.", parse_mode="Markdown")

# ================= GROUP MESSAGE FILTER =================
@bot.message_handler(content_types=['text'])
def check_abuse(message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.first_name or "User"

    # Skip admins
    member = bot.get_chat_member(chat_id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    # Skip authorized users
    if user_id in authorized_users.get(chat_id, set()):
        return

    text = normalize(message.text)

    for word in ABUSIVE_WORDS:
        if word in text:
            # Delete message
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass

            # Increase warning
            warnings[chat_id][user_id] += 1
            current_warn = warnings[chat_id][user_id]

            mention = f"[{username}](tg://user?id={user_id})"

            if current_warn >= MAX_WARNINGS:
                # Mute user
                try:
                    bot.restrict_chat_member(
                        chat_id,
                        user_id,
                        can_send_messages=False
                    )

                    # Inline unmute button
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

                warnings[chat_id][user_id] = 0  # reset
            else:
                bot.send_message(
                    chat_id,
                    f"{WARNING_MESSAGES.get(current_warn, '⚠️ {mention} warned.').format(mention=mention)}"
                )
            break

# ================= UNMUTE BUTTON =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("unmute:"))
def unmute_user(call):
    data = call.data.split(":")
    chat_id = int(data[1])
    user_id = int(data[2])

    # Only admins can unmute
    member = bot.get_chat_member(chat_id, call.from_user.id)
    if member.status not in ["administrator", "creator"]:
        bot.answer_callback_query(call.id, "Only admins can unmute!", show_alert=True)
        return

    try:
        bot.restrict_chat_member(chat_id, user_id, can_send_messages=True)
        bot.edit_message_text("✅ User unmuted by admin.", chat_id, call.message.message_id)
    except:
        pass

# ================= RUN BOT =================
if __name__ == "__main__":
    import main
    import time

    # Start Flask (if using main.app for health check)
    threading.Thread(target=main.app.run, kwargs={"host": "0.0.0.0", "port": 10000}).start()

    print("Bot is running...")
    bot.infinity_polling(skip_pending=True)
