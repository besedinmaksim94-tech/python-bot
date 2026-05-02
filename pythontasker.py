import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI

# ================= ЛОГИ =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

print("🔥 FILE STARTED")

# ================= ENV =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("TOKEN EXISTS:", bool(TELEGRAM_TOKEN))
print("OPENAI EXISTS:", bool(OPENAI_API_KEY))

# ЖЁСТКАЯ ПРОВЕРКА (чтобы не было silent crash)
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN is missing")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is missing")

# ================= INIT =================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

print("✅ BOT CREATED")
print("✅ OPENAI CLIENT CREATED")

# ================= START COMMAND =================

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "👋 Привет!\n\n"
        "🤖 Я AI бот\n"
        "Просто напиши вопрос."
    )

# ================= MAIN LOGIC =================

@dp.message()
async def handle_message(message: Message):
    text = message.text

    if not text:
        await message.answer("❗ Отправь текст")
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
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
        logging.exception("OPENAI ERROR")
        await message.answer(f"⚠️ OpenAI error:\n{e}")

# ================= START BOT =================

async def main():
    print("🚀 START POLLING")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("💥 FATAL ERROR:", e)