import os
import asyncio
import requests
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

WEB_APP_URL = "https://telegram-notes-app-zeta.vercel.app"
BACKEND_URL = "https://telegram-notes-app-5wnw.onrender.com"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Проверь файл .env в папке bot.")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть заметки",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ]
        ]
    )

    await message.answer(
        "Привет! Нажми кнопку ниже, чтобы открыть заметки.",
        reply_markup=keyboard
    )


async def check_reminders():
    while True:
        try:
            response = requests.get(f"{BACKEND_URL}/reminders/due", timeout=10)
            reminders = response.json()

            for reminder in reminders:
                note_id = reminder["id"]
                user_id = reminder["user_id"]
                title = reminder["title"]
                text = reminder["text"]

                message_text = (
                    "🔔 Напоминание по заметке\n\n"
                    f"📌 {title}\n\n"
                    f"{text}"
                )

                try:
                    await bot.send_message(chat_id=user_id, text=message_text)

                    requests.put(
                        f"{BACKEND_URL}/reminders/{note_id}/sent",
                        timeout=10
                    )

                except Exception as send_error:
                    print(f"Ошибка отправки напоминания {note_id}: {send_error}")

        except Exception as error:
            print(f"Ошибка проверки напоминаний: {error}")

        await asyncio.sleep(30)


async def main():
    asyncio.create_task(check_reminders())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())