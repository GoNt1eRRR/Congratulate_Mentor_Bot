import argparse
import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv

from bot.api.api_client import get_postcards, get_mentors

send_router = Router()


load_dotenv()


parser = argparse.ArgumentParser(description="Start Telegram Bot with specified URL")
parser.add_argument('--url', required=True, help="Specify the URL (TEST_URL for test, PROD_URL for production)")
args = parser.parse_args()

BASE_URL = os.getenv(args.url)


class SendPostcard(StatesGroup):
    choosing_mentor = State()
    choosing_postcard_type = State()
    choosing_postcard = State()
    confirming = State()


def fetch_data(api_func, error_message):
    data = api_func(BASE_URL)
    if not data:
        raise ValueError(error_message)
    return data


def format_mentor(mentor):
    first = mentor["name"]["first"].split()[0] if mentor["name"]["first"] else ""
    second = mentor["name"]["second"].split()[0] if mentor["name"]["second"] else ""
    return f"{mentor['tg_username']} {first} {second}"


@send_router.message(F.text == "Отправить Открытку")
async def choose_mentor(message: Message, state: FSMContext):
    try:
        mentors_data = fetch_data(get_mentors, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await message.answer(str(e))
        return

    mentors_list = mentors_data.get("mentors", [])
    if not mentors_list:
        await message.answer("Список менторов пока пуст. Попробуйте позже.")
        return

    keyboard = InlineKeyboardBuilder()
    for mentor in mentors_list:
        keyboard.button(text=format_mentor(mentor), callback_data=f"mentor:{mentor['id']}")
    keyboard.adjust(1)

    await message.answer("Выберите ментора:", reply_markup=keyboard.as_markup())
    await state.set_state(SendPostcard.choosing_mentor)


@send_router.callback_query(F.data.startswith("mentor:"))
async def mentor_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    mentor_id = int(callback.data.split(":")[1])
    try:
        mentors_data = fetch_data(get_mentors, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    mentor = next((m for m in mentors_data.get("mentors", []) if m["id"] == mentor_id), None)

    if not mentor:
        await callback.message.answer("Ментор не найден.")
        return

    await state.update_data(
        selected_mentor_id=mentor_id,
        selected_mentor_name=mentor["name"]["first"]
    )

    try:
        postcards_data = fetch_data(get_postcards, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    postcards_list = postcards_data.get("postcards", [])
    unique_types = list({postcard["name_ru"] for postcard in postcards_list})
    if not unique_types:
        await callback.message.answer("Список видов открыток пока пуст. Попробуйте позже")
        return

    keyboard = InlineKeyboardBuilder()
    for postcard_type in unique_types:
        keyboard.button(text=postcard_type, callback_data=f"postcard_type:{postcard_type}")
    keyboard.adjust(1)

    await callback.message.answer("Выберите тип открытки:", reply_markup=keyboard.as_markup())
    await state.set_state(SendPostcard.choosing_postcard_type)


@send_router.callback_query(F.data.startswith("postcard_type:"))
async def choose_postcard(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_type = callback.data.split(":", 1)[1]
    await state.update_data(selected_postcard_type=selected_type)

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
        await callback.message.answer("Нет открыток для выбранного типа.")
        return

    await callback.message.answer("Выберите открытку:")
    for postcard in filtered_postcards:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"Выбрать открытку (ID: {postcard['id']})",
            callback_data=f"postcard:{postcard['id']}"
        )
        builder.adjust(1)
        await callback.message.answer(postcard["body"], reply_markup=builder.as_markup())

    await state.set_state(SendPostcard.choosing_postcard)


@send_router.callback_query(F.data.startswith("postcard:"))
async def confirm_postcard(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    postcard_id = int(callback.data.split(":", 1)[1])
    await state.update_data(selected_postcard_id=postcard_id)

    data = await state.get_data()
    selected_type = data.get("selected_postcard_type", "")
    selected_mentor_name = data.get("selected_mentor_name", "Ментор")

    try:
        postcards_data = fetch_data(get_postcards, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    selected_postcard = next((postcard for postcard in postcards_data.get("postcards", []) if postcard["id"] == postcard_id), None)

    if not selected_postcard:
        await callback.message.answer("Выбранная открытка не найдена")
        return

    postcard_text = selected_postcard["body"].replace("#name", selected_mentor_name)
    confirming_message = (
        f"Вы выбрали открытку типа *{selected_type}*\n\n"
        f"Текст открытки:\n\n{postcard_text}\n\n"
        "Укажите, отправлять ли с указанием вашего имени?"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, указать отправителя", callback_data="send_with_sender")
    builder.button(text="Нет, без отправителя", callback_data="send_without_sender")
    builder.adjust(1)

    keyboard = builder.as_markup()

    await callback.message.answer(confirming_message, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(SendPostcard.confirming)


async def send_postcard_to_mentor(callback: CallbackQuery, state: FSMContext, include_sender: bool):
    await callback.answer()
    data = await state.get_data()
    selected_mentor_id = data.get("selected_mentor_id")
    selected_postcard_id = data.get("selected_postcard_id")
    selected_mentor_name = data.get("selected_mentor_name", "Ментор")

    try:
        mentors_data = fetch_data(get_mentors, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    try:
        postcards_data = fetch_data(get_postcards, "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    selected_mentor = next((mentor for mentor in mentors_data.get("mentors", []) if mentor["id"] == selected_mentor_id), None)

    selected_postcard = next((postcard for postcard in postcards_data.get("postcards", []) if postcard["id"] == selected_postcard_id), None)

    if not selected_mentor or not selected_postcard:
        await callback.message.answer("Выбранные ментор или открытка не найдены.")
        await state.clear()
        return

    postcard_body = selected_postcard["body"].replace("#name", selected_mentor_name)

    if include_sender:
        sender_info = f"\n\nОт: {callback.from_user.username}"
    else:
        sender_info = ""

    final_text = f"{postcard_body}{sender_info}"

    if selected_mentor.get("tg_chat_id"):
        try:
            await callback.bot.send_message(
                selected_mentor["tg_chat_id"], f"💌 Вам открытка!\n\n{final_text}"
            )
            await callback.message.answer("Открытка успешно отправлена! 🎉")
        except Exception as e:
            print(f"Ошибка отправки: {e}")
            await callback.message.answer(
                "Ошибка при отправке открытки ментору. Ментор мог заблокировать бота либо не начать с ним чат"
            )
    else:
        await callback.message.answer("У выбранного ментора отсутствует chat_id.")

    await state.clear()


@send_router.callback_query(F.data == "send_with_sender")
async def send_with_sender(callback: CallbackQuery, state: FSMContext):
    await send_postcard_to_mentor(callback, state, include_sender=True)


@send_router.callback_query(F.data == "send_without_sender")
async def send_without_sender(callback: CallbackQuery, state: FSMContext):
    await send_postcard_to_mentor(callback, state, include_sender=False)
