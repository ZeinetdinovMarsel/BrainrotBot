import random
import json
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler, MessageHandler, filters
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


async def send_random_word(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_IDS:
        return
    word = generate_word()
    for chat_id in CHAT_IDS:
        text = word
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            print(f"Ошибка при отправке в чат {chat_id}: {e}")

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    chat = update.effective_chat
    if status in ["member", "administrator"]:
        if chat.id not in CHAT_IDS:
            CHAT_IDS.append(chat.id)
            save_chats()
            print(f"Добавлен новый чат: {chat.title if chat.title else chat.id}, chat_id сохранён.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен")


async def register_by_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text.lower()
    tit_triggers = ["тить", "тит", "титька","tit"]

    if any(word in text for word in tit_triggers):
        chat = update.effective_chat

        if chat.id not in CHAT_IDS:
            CHAT_IDS.append(chat.id)
            save_chats()
            print(f"Зарегистрирован чат по слову: {chat.id}")

        gif_url = "https://media1.tenor.com/m/_6i1M6jDbNkAAAAd/dont-call-me-a-tit-youre-a-tit.gif"

        await update.message.reply_animation(
            animation=gif_url
        )

    nikita_triggers = ["никита", "некит", "никитос", "@Xonalz", "никитка","засранец","xonalz","xonal","nikita","никитыч","никиту","никит","никите","никиты"]

    if any(word in text for word in nikita_triggers):
        gif_url = "https://media1.tenor.com/m/Ah9iWbZYiVwAAAAC/капибара-zelko.gif"

        await update.message.reply_animation(
            animation=gif_url,
            reply_to_message_id=update.message.message_id
        )



def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .proxy(None)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register_by_word))
    app.add_handler(ChatMemberHandler(chat_member_update, chat_member_types=["my_chat_member"]))
    app.job_queue.run_repeating(send_random_word, interval=1800, first=5)

    print("Бот запущен...")
    app.run_polling()



if __name__ == "__main__":
    main()
