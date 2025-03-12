import argparse
import os

from aiogram import Router, F
from aiogram.types import Message
from dotenv import load_dotenv

from bot.keyboards import main_keyboard
from bot.api.api_client import get_mentors

start_router = Router()


load_dotenv()


parser = argparse.ArgumentParser(description="Start Telegram Bot with specified URL")
parser.add_argument('--url', required=True, help="Specify the URL (TEST_URL for test, PROD_URL for production)")
args = parser.parse_args()

BASE_URL = os.getenv(args.url)


def fetch_data(api_func, error_message):
    data = api_func(BASE_URL)
    if not data:
        raise ValueError(error_message)
    return data


@start_router.message(F.text == "/start")
async def start_handler(message: Message):
    username = message.from_user.username
    chat_id = message.chat.id

    try:
        mentors_data = fetch_data(get_mentors, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await message.answer(str(e))
        return

    mentors_list = mentors_data.get("mentors", [])

    mentor = next((m for m in mentors_list if m["tg_chat_id"] == chat_id), None)

    if mentor:
        text = (
            f'🎉 Привет, Ментор {mentor["name"]["first"]}! 🎉\n\n'
            'Это бот для отправки поздравлений ментору ❤️\n\n'
            '✨ Нажмите кнопку "ОТПРАВИТЬ ОТКРЫТКУ" чтобы отправить поздравления! ✨'
        )
        keyboard = main_keyboard
    else:
        text = (
            f'🎉 Привет, Ученик {username}! 🎉\n\n'
            'Это бот для отправки поздравлений ментору ❤️\n\n'
            '✨ Нажмите кнопку "ОТПРАВИТЬ ОТКРЫТКУ" чтобы порадовать своего ментора! ✨'
        )
        keyboard = main_keyboard

    await message.answer(text, reply_markup=keyboard)
