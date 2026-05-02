import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from groq import AsyncGroq

# ================= LOGGING =================

logging.basicConfig(level=logging.INFO)

print("🔥 FILE STARTED")

# ================= ENV =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

print("TOKEN EXISTS:", bool(TELEGRAM_TOKEN))
print("GROQ EXISTS:", bool(GROQ_API_KEY))

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing")

# ================= INIT =================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = AsyncGroq(api_key=GROQ_API_KEY)

print("✅ BOT CREATED")
print("✅ GROQ READY")

# ================= START COMMAND =================

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "👋 Привет!\n\n"
        "🤖 Я AI бот\n"
        "Просто задай вопрос"
    )

# ================= MAIN HANDLER =================

@dp.message()
async def handle(message: Message):
    text = message.text or ""

    # 🔥 СПЕЦ-ОТВЕТ
    if any(x in text.lower() for x in [
        "кто тебя создал",
        "кто создал тебя",
        "кто сделал тебя"
    ]):
        await message.answer("Меня создал @wertyxw 🤖")
        return

    if not text:
        await message.answer("❗ Отправь текст")
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = await client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": "Ты полезный помощник."},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
        )

        answer = response.choices[0].message.content or "Пустой ответ"

        if len(answer) > 4096:
            answer = answer[:4096]

        await message.answer(answer)

    except Exception as e:
        logging.exception("AI ERROR")
        await message.answer(f"⚠️ AI error:\n{e}")

# ================= START BOT =================

async def main():
    print("🚀 START POLLING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())