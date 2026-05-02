import asyncio
import logging
import os
import time
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from groq import AsyncGroq

# ================= CONFIG =================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN or not GROQ_API_KEY:
    raise ValueError("❌ Нет переменных окружения")

bot = Bot(token=TOKEN)
dp = Dispatcher()
client = AsyncGroq(api_key=GROQ_API_KEY)

DB = "bot.db"

# ================= DB =================

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            mode TEXT DEFAULT 'assistant'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
        """)
        await db.commit()

async def set_mode(user_id, mode):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, mode) VALUES (?, ?)",
            (user_id, mode)
        )
        await db.commit()

async def get_mode(user_id):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT mode FROM users WHERE user_id=?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else "assistant"

async def add_msg(user_id, role, content):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()

async def get_history(user_id, limit=10):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        ) as cur:
            rows = await cur.fetchall()
            return list(reversed(rows))

# ================= UI =================

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📚 Учитель", callback_data="teacher"),
            InlineKeyboardButton(text="💻 Кодер", callback_data="coder")
        ],
        [
            InlineKeyboardButton(text="😂 Юмор", callback_data="fun"),
            InlineKeyboardButton(text="🤖 Обычный", callback_data="assistant")
        ]
    ])

# ================= STREAM =================

async def stream_send(message: Message, text: str):
    msg = await message.answer("🤖 ...")
    buffer = ""

    for ch in text:
        buffer += ch
        if len(buffer) % 25 == 0:
            await msg.edit_text(buffer)
            await asyncio.sleep(0.03)

    await msg.edit_text(buffer)

# ================= GROQ =================

async def ask_groq(messages, mode):
    system_map = {
        "assistant": "Ты полезный помощник.",
        "teacher": "Ты учитель, объясняешь просто.",
        "coder": "Ты программист, даёшь код.",
        "fun": "Ты шутишь и отвечаешь весело."
    }

    sys = system_map.get(mode, system_map["assistant"])

    msgs = [{"role": "system", "content": sys}]
    for r, c in messages:
        msgs.append({"role": r, "content": c})

    last_error = None

    for i in range(3):
        try:
            return await client.chat.completions.create(
                model="llama3-8b-8192",  # 🔥 стабильная модель
                messages=msgs,
                temperature=0.7,
            )
        except Exception as e:
            last_error = e
            await asyncio.sleep(1.5 * (i + 1))

    raise last_error

# ================= START =================

@dp.message(F.text == "/start")
async def start(message: Message):
    await init_db()
    await set_mode(message.from_user.id, "assistant")

    await message.answer(
        "👋 Привет!\nВыбери режим:",
        reply_markup=menu()
    )

# ================= MODE =================

@dp.callback_query()
async def cb(call: CallbackQuery):
    await set_mode(call.from_user.id, call.data)
    await call.message.edit_text(f"✅ Режим: {call.data}")

# ================= MAIN =================

last_request = {}
COOLDOWN = 2

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if not text:
        return

    # антиспам
    now = time.time()
    if now - last_request.get(user_id, 0) < COOLDOWN:
        await message.answer("⏳ Подожди...")
        return
    last_request[user_id] = now

    # создатель
    if "кто тебя создал" in text.lower():
        await message.answer("Меня создал @wertyxw 🤖")
        return

    await add_msg(user_id, "user", text)
    history = await get_history(user_id)
    mode = await get_mode(user_id)

    try:
        response = await ask_groq(history, mode)
        answer = response.choices[0].message.content

        await add_msg(user_id, "assistant", answer)

        await stream_send(message, answer)

    except Exception as e:
        print("FULL ERROR:", repr(e))  # 🔥 теперь видно реальную ошибку
        await message.answer(f"⚠️ Ошибка AI:\n{e}")

# ================= RUN =================

async def main():
    print("🚀 BOT STARTED")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())