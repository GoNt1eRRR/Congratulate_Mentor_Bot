import argparse
import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from bot.api.api_client import get_postcards

view_postcards_router = Router()

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


@view_postcards_router.message(F.text == "Виды Открыток")
async def display_postcard_types(message: Message):
    try:
        postcards_data = fetch_data(get_postcards, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await message.answer(str(e))
        return

    postcards_list = postcards_data.get("postcards", [])

    unique_types = list({postcard["name_ru"] for postcard in postcards_list})
    if not unique_types:
        await message.answer("Список видов открыток пока пуст. Попробуйте позже.")
        return

    keyboard = InlineKeyboardBuilder()
    for postcard_type in unique_types:
        keyboard.button(text=postcard_type, callback_data=f"view_postcard_type:{postcard_type}")
    keyboard.adjust(1)

    await message.answer("Выберите тип открытки:", reply_markup=keyboard.as_markup())


@view_postcards_router.callback_query(F.data.startswith("view_postcard_type:"))
async def display_postcards(callback: CallbackQuery):
    await callback.answer()
    selected_type = callback.data.split(":", 1)[1]

    try:
        postcards_data = fetch_data(get_postcards, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    filtered_postcards = [
        postcard for postcard in postcards_data.get("postcards", [])
        if postcard["name_ru"] == selected_type
    ]

    if not filtered_postcards:
        await callback.message.answer("Нет открыток для выбранного типа")
        return

    for postcard in filtered_postcards:
        postcard_text = f"Открытка (ID: {postcard['id']}):\n{postcard['body']}"
        await callback.message.answer(postcard_text)
