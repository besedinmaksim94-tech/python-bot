import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from groq import AsyncGroq

# ================= LOG =================

logging.basicConfig(level=logging.INFO)
print("🔥 FILE STARTED")

# ================= ENV =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

# ================= INIT =================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = AsyncGroq(api_key=GROQ_API_KEY)

print("✅ BOT READY")

# ================= RETRY WRAPPER =================

async def ask_ai(messages):
    last_error = None

    for i in range(3):
        try:
            return await client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                temperature=0.7,
            )
        except Exception as e:
            last_error = e
            await asyncio.sleep(1.5 * (i + 1))

    raise last_error

# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Привет! Я AI бот. Просто напиши вопрос.")

# ================= MAIN =================

@dp.message()
async def handle(message: Message):
    text = (message.text or "").strip()

    # 🔥 спец-ответ
    if any(x in text.lower() for x in [
        "кто тебя создал",
        "кто создал тебя",
        "кто сделал тебя"
    ]):
        await message.answer("Меня создал @wertyxw 🤖")
        return

    # защита от пустого
    if not text:
        await message.answer("❗ Отправь текстовое сообщение")
        return

    # защита от слишком длинного
    if len(text) > 3000:
        text = text[:3000]

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = await ask_ai([
            {"role": "system", "content": "Ты полезный помощник."},
            {"role": "user", "content": text}
        ])

        answer = response.choices[0].message.content or "Пустой ответ"

        if len(answer) > 4096:
            answer = answer[:4096]

        await message.answer(answer)

    except Exception as e:
        logging.exception("AI ERROR")
        await message.answer("⚠️ AI временно недоступен, попробуй позже")

# ================= START BOT =================

async def main():
    print("🚀 START POLLING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())