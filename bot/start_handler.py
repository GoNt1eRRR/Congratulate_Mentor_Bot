from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards import main_keyboard
from libs.api_client import get_mentors
from bot.utils import get_url, validate_api_response


start_router = Router()

BASE_URL = get_url()
SCHEMA_FILE = "libs/schema.json"


@start_router.message(F.text == "/start")
async def start_handler(message: Message):
    username = message.from_user.username
    chat_id = message.chat.id

    try:
        mentors_response = validate_api_response(get_mentors(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await message.answer(str(e))
        return

    mentors = mentors_response.get("mentors", [])

    mentor = next((m for m in mentors if m["tg_chat_id"] == chat_id), None)

    role = "Ментор" if mentor else "Ученик"
    name = mentor["name"]["first"] if mentor else username
    action = "отправить поздравления" if mentor else "порадовать своего ментора"

    text = (
        f"🎉 Привет, {role} {name}! 🎉\n\n"
        "Это бот для отправки поздравлений ментору ❤️\n\n"
        f"✨ Нажмите кнопку 'ОТПРАВИТЬ ОТКРЫТКУ', чтобы {action}! ✨"
    )

    await message.answer(text, reply_markup=main_keyboard)
