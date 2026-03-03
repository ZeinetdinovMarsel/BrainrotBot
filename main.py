import random
import json
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler,
)

TOKEN = "8414039519:AAG3nIb4SPVX9SbqAHodOkL5GEtV9jhJoLM"
FILE = "chats.json"

consonants = list("бвгджзклмнпрстфхцчш ")
vowels = list("аеиоуыюя")
endings = ["ть"] * 15 + ["дь","вь", "зь", "сь", "вь", "рь", "й", "тя", "дя","ня"]
prefixes = [""] * 40 + ["би", "ви", "ва", "ны","ж"]

try:
    with open(FILE, "r") as f:
        CHAT_IDS = json.load(f)
except FileNotFoundError:
    CHAT_IDS = []


def save_chats():
    with open(FILE, "w") as f:
        json.dump(CHAT_IDS, f)


special_words = ["7у7","8471"]


def generate_word():
    if random.random() < 0.01:
        return random.choice(special_words)
    prefix = random.choice(prefixes)
    consonant = random.choice(consonants)
    vowel = random.choice(vowels)
    ending = random.choice(endings)
    return prefix + consonant + vowel + ending


async def send_random_words_loop(app):
    await app.initialize()
    await app.start()
    bot = app.bot
    while True:
        if CHAT_IDS:
            word = generate_word()
            for chat_id in CHAT_IDS:
                try:
                    await bot.send_message(chat_id=chat_id, text=word)
                except Exception as e:
                    print(f"Ошибка при отправке в чат {chat_id}: {e}")
        await asyncio.sleep(5)


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    chat = update.effective_chat
    if status in ["member", "administrator"]:
        if chat.id not in CHAT_IDS:
            CHAT_IDS.append(chat.id)
            save_chats()
            print(f"Добавлен новый чат: {chat.title if chat.title else chat.id}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(chat_member_update, chat_member_types=["my_chat_member"]))

    asyncio.create_task(send_random_words_loop(app))

    print("Бот запущен...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())