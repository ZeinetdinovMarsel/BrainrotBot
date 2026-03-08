import random
import json
import os
import time
from datetime import datetime
from collections import defaultdict, deque
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    filters
)

TOKEN = "8414039519:AAG3nIb4SPVX9SbqAHodOkL5GEtV9jhJoLM"
FILE = "chats.json"
MEMORY_FILE = "bot_brain.json"

# === СЛОВАРИ ПОДЪЁБОВ ===
# Формат: {триггер: [ответы]}, {user} подставится автоматически
TRIGGERS = {

    "рофл": [
        "Ржу не могу",
        "Не смешно, но ладно",
    ],

    # ---------- Капс (дополнено) ----------
    "капс": [
        "ЧЁ ТЫ ОРЁШЬ? Я не глухая",
        "Тише,  уши вянут",
        "Орёшь как потерпевший",
    ],

    # ---------- НОВЫЕ ТРИГГЕРЫ ----------

    # Реакция на благодарность
    "спасибо": [
        "Не за что, иди нахуй",
        "Пожалуйста, только больше не пиши",
    ],

    # Реакция на извинения
    "извини": [
        "Извини, но мне похуй",
        "Извинись перед своей мамой за то, что ты таким уродился",
    ],

    # Вопрос "почему"
    "почему": [
        "Потому что гладиолус",
        "Потому что ебало кривое",
    ],




    "нет": [
        "Пидора ответ",
        "Шлюхи аргумент",
        "Сделаю минет"
    ],

    # Согласие
    "да": [
        "Пизда",
        "Хуй на"
    ],


    # Оскорбления "тупой"
    "тупой": [
        "Мать твоя тупая",
        "Отец у тебя тупой"
    ],


    "заткнись": [
        "Сам заткнись, я только начал.",
        "Ты сначала сам заткнись"
        "Сам ебло ты завали"
    ],

    "бля": [
        "Бля? Сам ты бля.",
    ],
    "сука": [
        "Сука это ты?",
        "Не груби.",
    ],
}

# ---------- ВРЕМЕННЫЕ РЕАКЦИИ (дополнено) ----------
TIME_REACTIONS = {
    "morning": [  # 6-11
        "Доброе утро, хуесосы",
        "Утро блять только началось а @Xonalz опять обосрался",
        "Проснулись, потянулись, нахуй пошли",
        "Утро вечера мудренее, но вы всё равно выблядки",
        "С утра пораньше @Xonalz насрал на кровать",
    ],
    "day": [  # 11-18
        "День в разгаре, а {user} уже говно и в говно",
        "Днём нужно работать, а {user} дрочить",
    ],
    "evening": [  # 18-23
        "Вечер, {user}. Устал? А я нет, я бот, мне похуй.",
        "Вечером самое время тупить, чем {user} и занимается.",
    ],
    "night": [  # 23-6
        "Ночной бред от {user} — мой любимый жанр",
    ],
}

# Генератор псевдо-слов (твой, но с доработкой)
consonants = list("бвгджзклмнпрстфхцчшщ")
vowels = list("аеиоуыэюя")
endings = ["ть", "дь", "вить", "зить", "сить", "рить", "й", "тя", "дя", "ня", "нуть", "ануть", "ебнуть"]
prefixes = [""] * 30 + ["би", "ви", "ва", "ны", "ж", "за", "про", "еба", "пиздо", "хуе"]
special_words = ["7у7", "8471", "хуйло", "рофл", "кринж", "жоска", "ахуенно", "похуй"]


def generate_word():
    if random.random() < 0.07:
        return random.choice(special_words)
    prefix = random.choice(prefixes)
    syllable = random.choice(consonants) + random.choice(vowels)
    if random.random() > 0.4:
        syllable += random.choice(consonants)
    ending = random.choice(endings)
    return prefix + syllable + ending


# === ПАМЯТЬ И МОЗГ БОТА ===
class BotBrain:
    def __init__(self, max_msgs=100):
        self.chats = defaultdict(lambda: deque(maxlen=max_msgs))
        self.stats = defaultdict(lambda: defaultdict(lambda: {"count": 0, "last_seen": 0}))
        self.mood = defaultdict(lambda: {"toxic": 0.3, "active": 0})  # Настроение по чату
        self.load()

    def add_message(self, chat_id, user_id, user_name, text):
        self.chats[chat_id].append({
            "user_id": user_id,
            "user_name": user_name,
            "text": text,
            "time": time.time()
        })
        self.stats[chat_id][user_id]["count"] += 1
        self.stats[chat_id][user_id]["last_seen"] = time.time()
        # Чем больше сообщений — тем токсичнее бот к этому юзеру
        if self.stats[chat_id][user_id]["count"] > 15:
            self.mood[chat_id]["toxic"] = min(1.0, self.mood[chat_id]["toxic"] + 0.05)

    def get_recent(self, chat_id, limit=10):
        return list(self.chats[chat_id])[-limit:]

    def get_random_msg(self, chat_id, exclude_user=None):
        msgs = [m for m in self.chats[chat_id] if m['user_id'] != exclude_user]
        return random.choice(msgs) if msgs else None

    def get_most_active(self, chat_id, last_minutes=30):
        now = time.time()
        candidates = {
            uid: data for uid, data in self.stats[chat_id].items()
            if now - data["last_seen"] < last_minutes * 60
        }
        if not candidates: return None
        return max(candidates, key=lambda x: candidates[x]["count"])

    def get_time_period(self):
        hour = datetime.now().hour
        if 6 <= hour < 11:
            return "morning"
        elif 11 <= hour < 18:
            return "day"
        elif 18 <= hour < 23:
            return "evening"
        else:
            return "night"

    def save(self):
        data = {
            "chats": {cid: list(msgs) for cid, msgs in self.chats.items()},
            "stats": {cid: dict(users) for cid, users in self.stats.items()},
            "mood": dict(self.mood)
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, msgs in data.get("chats", {}).items():
                        self.chats[int(cid)] = deque(msgs, maxlen=100)
                    for cid, stats in data.get("stats", {}).items():
                        self.stats[int(cid)] = defaultdict(
                            lambda: {"count": 0, "last_seen": 0},
                            {int(k): v for k, v in stats.items()}
                        )
                    for cid, mood in data.get("mood", {}).items():
                        self.mood[int(cid)] = mood
            except:
                pass


brain = BotBrain()

# === ЗАГРУЗКА ЧАТОВ ===
try:
    with open(FILE, "r") as f:
        CHAT_IDS = json.load(f)
except FileNotFoundError:
    CHAT_IDS = []


def save_chats():
    with open(FILE, "w") as f:
        json.dump(CHAT_IDS, f)
    brain.save()


# === ГЕНЕРАЦИЯ ОТВЕТА ===
def generate_response(chat_id, user_id, user_name, text):
    text_lower = text.lower()
    mood = brain.mood[chat_id]
    period = brain.get_time_period()

    # Шанс ответа зависит от настроения и активности
    base_chance = 0.2 + mood["toxic"] * 0.3
    if random.random() > base_chance:
        return None

    # 1. Проверка триггеров по словам
    for trigger, responses in TRIGGERS.items():
        if trigger in text_lower:
            resp = random.choice(responses)
            return resp.format(user=user_name) if "{user}" in resp else resp

    # 2. Реакция на капс
    if text.isupper() and len(text) > 5:
        return f"ЧЁ ТЫ ОРЁШЬ, {user_name}? Я не глухой."

    # 3. Реакция на вопросы (много "?")
    if text.count("?") >= 2:
        return f"{user_name}, ты чё, допрос устраиваешь? Спокойнее."

    # 4. Если юзер флудит — персональный подъёб
    if brain.stats[chat_id][user_id]["count"] > 20:
        rofls = [
            f"{user_name}, ебать ты разговорчивый. Заткни ебало",
            f"Опять {user_name}? Мы тут уже счёт потеряли",
            f"{user_name}, напиши книгу, а не в чат."
        ]
        return random.choice(rofls)

    # 5. Время суток + упоминание самого активного
    if random.random() < 0.3:
        active = brain.get_most_active(chat_id)
        if active and active != user_id:
            active_name = next((m["user_name"] for m in brain.chats[chat_id] if m["user_id"] == active), "кто-то")
            time_responses = TIME_REACTIONS.get(period, [])
            return random.choice(time_responses).format(user=active_name)

    # 6. Цитирование чата (бот "слушает")
    if random.random() < 0.25:
        msg = brain.get_random_msg(chat_id, exclude_user=user_id)
        if msg:
            variants = [
                f"А вот тут написали: «{msg['text']}». Бред, да {user_name}?",
                f"Слышь, {user_name}, а ты видел: {msg['text']}",
                f"Пиздец, {msg['text']} — это сильно."
            ]
            return random.choice(variants)

    # 7. Дефолтные ответы с учётом настроения
    if mood["toxic"] > 0.7:
        toxic = [f"Нахуй, {user_name}.", "Иди нахуй со своим текстом.", "Бред."]
        return random.choice(toxic)
    else:
        chill = ["Ага.", "Ну ок.", "Жиза.", "Ржач.", "Чё?", "Ау.", "Кто тут?", "Дальше."]
        return random.choice(chill)


# === ФОНОВЫЕ СОБЫТИЯ ===
async def background_activity(context: ContextTypes.DEFAULT_TYPE):
    """Периодически бот пишет что-то сам"""
    if not CHAT_IDS: return

    for chat_id in CHAT_IDS:
        # 20% шанс что-то написать в каждый чат
        if random.random() > 0.2: continue

        action = random.choice(["word", "quote", "time_rofl", "nothing"])

        if action == "word":
            text = generate_word()
        elif action == "quote":
            msg = brain.get_random_msg(chat_id)
            if msg:
                text = f"Цитата дня: «{msg['text']}» — {msg['user_name']}"
            else:
                text = generate_word()
        elif action == "time_rofl":
            period = brain.get_time_period()
            responses = TIME_REACTIONS.get(period, ["Время — хуйня, а чат вечен."])
            text = random.choice(responses).format(user="все")
        else:
            continue  # nothing

        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"BG Error {chat_id}: {e}")

        # Пауза между отправками в разные чаты
        await asyncio.sleep(2)


# === ОБРАБОТКА СООБЩЕНИЙ ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Анон"
    text = update.message.text

    # Если чат новый — добавляем
    if chat_id not in CHAT_IDS:
        CHAT_IDS.append(chat_id)
        save_chats()

    # Сохраняем в память
    brain.add_message(chat_id, user_id, user_name, text)

    # Проверяем, стоит ли отвечать
    response = generate_response(chat_id, user_id, user_name, text)

    if response:
        # Небольшая задержка для "естественности"
        await asyncio.sleep(random.uniform(0.5, 2.0))
        try:
            await update.message.reply_text(response)
        except Exception as e:
            print(f"Reply error: {e}")


# === ПРИСОЕДИНЕНИЕ К ЧАТУ ===
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.my_chat_member.new_chat_member.status
    chat = update.effective_chat
    if status in ["member", "administrator"]:
        if chat.id not in CHAT_IDS:
            CHAT_IDS.append(chat.id)
            save_chats()
            # Первое сообщение без команд
            phrases = [
                "О, меня добавили. Ну всё, идите нахуй",
            ]
            await context.bot.send_message(chat.id, random.choice(phrases))


# === ЗАПУСК ===
def main():
    import asyncio
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    # Только message handler — никаких команд!
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(chat_member_update, chat_member_types=["my_chat_member"]))

    # Фоновые задачи
    # Каждые 20-40 минут бот что-то пишет сам
    app.job_queue.run_repeating(
        background_activity,
        interval=random.randint(1200, 2400),
        first=300
    )

    # Сохранение каждые 5 минут
    def auto_save(context):
        brain.save()

    app.job_queue.run_repeating(auto_save, interval=300)

    app.run_polling()


if __name__ == "__main__":
    import asyncio

    main()