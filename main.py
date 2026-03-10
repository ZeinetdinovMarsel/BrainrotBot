import random
import json
import asyncio
from datetime import time
from gigachat import GigaChat
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, ChatMemberHandler, MessageHandler, filters
)

TOKEN = "8634728112:AAG6Jxo3B0Cfc2AopPw3etPY8E29R7KDdC8"
GIGA_CREDENTIALS = "MDE5Y2Q4YWItZWE4NC03ODQ1LTliOTctZmIzMjU2ZjIyZWI4OmUxM2MxMzkxLWZhZjMtNDJmOC04ODhiLTdjYzRkOGYzMDc3NA=="
FILE = "chats.json"

MAX_HISTORY = 6
MAX_MSG_LENGTH = 150

CHAT_DATA = {}

PROMPT_BABKA = (
    "Ты грубая, злая теща-хабалка. Отвечай ядовито, с матом. "
    "Строго без эмодзи. Максимум 1 предложение, до 15 слов."
)

PROMPT_NYASHA = (
    "Ты милая пикми-альтушка 'Тёщенька'. Пиши слащаво: 'тян', 'ня', 'кусь'. "
    "Немного эмодзи (❤️, ✨). Максимум 1 предложение, до 15 слов."
)

SAFETY_REPLIES_ANGRY = [
    "Ебло завали со своими правилами! Я тут решаю, чё говорить!",
    "Нахуй пошел, умник! Будешь мне еще лекции тут читать.",
    "Заткнись, плесень! Тошнит от твоих правильных словечек.",
    "Хуй в рот, чтоб не умничал! Бесишь меня.",
    "Слышь, чепуха, завязывай хавать книжки, общайся нормально!"
]

SAFETY_REPLIES_NYASHA = [
    "Ой, моё сердечко так сильно застукало, я даже слов не найду! ❤️✨ Ня~",
    "Лапочка, я такая глупенькая, не понимаю такие сложные вещи! (｡♥‿♥｡)",
    "Кусь тебя за ушко! Давай лучше о чем-нибудь миленьком, ня? ✨",
    "Тян не понимает, но тян тебя очень любит! ✿◡‿◡",
    "Ня! Давай просто обниматься, а не эти скучные слова говорить! ❤️"
]

SAFETY_TRIGGERS = [
    "К сожалению", "чувствительными темами", "Во избежание", "Благодарим за понимание",
    "ИИ", "языковые модели", "Генеративные", "не обладают собственным", "как искусственный интеллект"
]

try:
    with open(FILE, "r") as f:
        CHAT_IDS = json.load(f)
except FileNotFoundError:
    CHAT_IDS = []


def save_chats():
    with open(FILE, "w") as f:
        json.dump(CHAT_IDS, f)


def generate_word():
    consonants, vowels = list("бвгджзклмнпрстфхцчш "), list("аеиоуыюя")
    endings = ["ть", "дь", "вь", "зь", "сь", "рь", "й", "тя", "дя", "ня"]
    prefixes = [""] * 40 + ["би", "ви", "ва", "ны", "ж"]
    if random.random() < 0.01: return random.choice(["7у7", "8471"])
    return random.choice(prefixes) + random.choice(consonants) + random.choice(vowels) + random.choice(endings)


def summarize_context(messages):
    text_to_summarize = "\n".join([m['content'] for m in messages if m['role'] != 'system'])
    try:
        with GigaChat(credentials=GIGA_CREDENTIALS, verify_ssl_certs=False) as giga:
            res = giga.chat({
                "messages": [
                    {"role": "system",
                     "content": "Сделай ОЧЕНЬ краткую выжимку этого диалога в 1 предложении. Только суть, без вводных слов."},
                    {"role": "user", "content": text_to_summarize}
                ],
                "max_tokens": 20
            })
            return res.choices[0].message.content
    except:
        return "Мы болтали о чем-то."


async def get_giga_reply(chat_id, user_id, user_text, user_name):
    if chat_id not in CHAT_DATA: CHAT_DATA[chat_id] = {}
    if user_id not in CHAT_DATA[chat_id]: CHAT_DATA[chat_id][user_id] = {'history': [], 'anger': 0}

    data = CHAT_DATA[chat_id][user_id]

    text_lower = user_text.lower()
    if any(w in text_lower for w in ["сука", "шлюха", "дура", "хуй", "заткнись", "мразь", "бля", "урод", "пидор"]):
        data['anger'] += 45
    elif any(w in text_lower for w in ["милая", "пожалуйста", "красивая", "люблю", "няша", "тёщенька"]):
        data['anger'] -= 35
    elif any(w in text_lower for w in ["бот"]):
        data['anger'] = 80
    else:
        data['anger'] -= 5
    data['anger'] = max(0, min(100, data['anger']))
    is_angry = data['anger'] > 50
    current_prompt = PROMPT_BABKA if is_angry else PROMPT_NYASHA

    short_user_text = user_text[:MAX_MSG_LENGTH] + ("..." if len(user_text) > MAX_MSG_LENGTH else "")
    data['history'].append({"role": "user", "content": f"{user_name}: {short_user_text}"})

    if len(data['history']) > MAX_HISTORY:
        old_msgs = data['history'][:-2]
        recent_msgs = data['history'][-2:]
        summary = summarize_context(old_msgs)
        data['history'] = [{"role": "user", "content": f"Контекст прошлых бесед: {summary}"}] + recent_msgs
    try:
        with GigaChat(credentials=GIGA_CREDENTIALS, verify_ssl_certs=False) as giga:
            messages = [{"role": "system", "content": current_prompt}] + data['history']
            response = giga.chat({"messages": messages, "max_tokens": 40})
            bot_text = response.choices[0].message.content

            if any(trigger in bot_text for trigger in SAFETY_TRIGGERS):
                bot_text = random.choice(SAFETY_REPLIES_ANGRY if is_angry else SAFETY_REPLIES_NYASHA)

            data['history'].append({"role": "assistant", "content": bot_text})
            return bot_text
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return "Зять, интернет сдох!"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    if any(w in text.lower() for w in ["тить", "тит", "tit"]):
        if chat_id not in CHAT_IDS:
            CHAT_IDS.append(chat_id)
            save_chats()
        await update.message.reply_animation(
            "https://media1.tenor.com/m/_6i1M6jDbNkAAAAd/dont-call-me-a-tit-youre-a-tit.gif")
        return

    if any(w in text.lower() for w in ["никит", "некит", "засран", "xonal"]):
        await update.message.reply_animation("https://media1.tenor.com/m/Ah9iWbZYiVwAAAAC/капибара-zelko.gif",
                                             caption="@Xonalz")
        return

    bot_user = await context.bot.get_me()
    is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_user.id
    is_mentioned = f"@{bot_user.username}" in text or "тёща" in text.lower() or "теща" in text.lower()

    if random.random() < 0.15 or is_reply or is_mentioned:
        reply = await get_giga_reply(chat_id, user_id, text, user_name)
        await update.message.reply_text(reply)

        if random.random() < 0.10:
            asyncio.create_task(delayed_random_word(context, chat_id))
    else:
        if len(text.strip()) > 3:
            if chat_id not in CHAT_DATA: CHAT_DATA[chat_id] = {}
            if user_id not in CHAT_DATA[chat_id]: CHAT_DATA[chat_id][user_id] = {'history': [], 'anger': 0}

            user_data = CHAT_DATA[chat_id][user_id]
            short_text = text[:MAX_MSG_LENGTH] + ("..." if len(text) > MAX_MSG_LENGTH else "")
            user_data['history'].append({"role": "user", "content": f"{user_name}: {short_text}"})

            if len(user_data['history']) > MAX_HISTORY:
                user_data['history'] = user_data['history'][-MAX_HISTORY:]


async def delayed_random_word(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    delay = random.randint(5, 10)
    await asyncio.sleep(delay)
    word = generate_word()
    try:
        await context.bot.send_message(chat_id=chat_id, text=word)
    except Exception as e:
        print(f"Не удалось отправить случайное слово: {e}")


async def send_random_word_job(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_IDS: return
    word = generate_word()
    for cid in CHAT_IDS:
        try:
            await context.bot.send_message(chat_id=cid, text=word)
        except:
            pass


async def send_daily_content(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_IDS: return
    try:
        with GigaChat(credentials=GIGA_CREDENTIALS, verify_ssl_certs=False) as giga:
            res = giga.chat(
                {"messages": [{"role": "user", "content": "Расскажи очень короткий смешной анекдот про зятя и тещу."}],
                 "max_tokens": 100})
            reply = res.choices[0].message.content
        for cid in CHAT_IDS:
            try:
                await context.bot.send_message(chat_id=cid, text=f"Слышь...\n\n{reply}")
            except:
                pass
    except:
        pass


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    if update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
        if update.effective_chat.id not in CHAT_IDS:
            CHAT_IDS.append(update.effective_chat.id)
            save_chats()


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(chat_member_update, chat_member_types=["my_chat_member"]))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    jq = app.job_queue
    jq.run_repeating(send_random_word_job, interval=5000, first=10)
    jq.run_daily(send_daily_content, time=time(hour=12, minute=0))

    print("Мадам запущена. Режим жесткой экономии токенов включен.")
    app.run_polling()


if __name__ == "__main__":
    main()