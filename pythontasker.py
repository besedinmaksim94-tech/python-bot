import asyncio
import logging
import os
import aiohttp
import aiosqlite
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ================= LOG =================

logging.basicConfig(level=logging.INFO)
print("🔥 PRO BOT STARTED")

# ================= ENV =================

TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

DB = "bot.db"

if not TOKEN or not HF_API_KEY:
    raise ValueError("Missing env vars")

bot = Bot(token=TOKEN)
dp = Dispatcher()

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

# ================= UI BUTTONS =================

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

# ================= HF =================

async def ask_hf(prompt):
    url = "https://api-inference.huggingface.co/models/google/flan-t5-large"

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 250,
            "temperature": 0.7
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()

            if isinstance(data, list):
                return data[0].get("generated_text", "")

            return str(data)

# ================= STREAM (fake typing) =================

async def stream_send(message: Message, text: str):
    msg = await message.answer("🤖 ...")

    buffer = ""
    for ch in text:
        buffer += ch
        if len(buffer) % 20 == 0:
            await msg.edit_text(buffer)
            await asyncio.sleep(0.05)

    await msg.edit_text(buffer)

# ================= START =================

@dp.message(F.text == "/start")
async def start(message: Message):
    await init_db()
    await set_mode(message.from_user.id, "assistant")

    await message.answer(
        "👋 Привет! Я AI бот для различных целей\nВыбери режим:",
        reply_markup=menu()
    )

# ================= CALLBACK =================

@dp.callback_query()
async def cb(call: CallbackQuery):
    mode = call.data
    await set_mode(call.from_user.id, mode)

    await call.message.edit_text(f"✅ Режим установлен: {mode}")

# ================= CHAT =================

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if not text:
        return

    # спец-ответ
    if "кто тебя создал" in text.lower():
        await message.answer("Меня создал @wertyxw 🤖")
        return

    mode = await get_mode(user_id)

    await add_msg(user_id, "user", text)

    history = await get_history(user_id)

    prompt = f"Mode: {mode}\n" + "\n".join([f"{r}: {c}" for r, c in history])

    try:
        answer = await ask_hf(prompt)

        await add_msg(user_id, "assistant", answer)

        # streaming эффект
        await stream_send(message, answer)

    except Exception as e:
        print("FULL ERROR:", repr(e))
        await message.answer(f"⚠️ DEBUG:\n{e}")

# ================= RUN =================

async def main():
    print("🚀 START POLLING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())