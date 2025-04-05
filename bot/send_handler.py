from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from libs.api_client import get_postcards, get_mentors
from bot.utils import get_url, validate_api_response, format_mentor


send_router = Router()

BASE_URL = get_url()
SCHEMA_FILE = "libs/schema.json"


class SendPostcard(StatesGroup):
    choosing_mentor = State()
    choosing_postcard_type = State()
    choosing_postcard = State()
    confirming = State()


@send_router.message(F.text == "Отправить Открытку")
async def choose_mentor(message: Message, state: FSMContext):
    try:
        mentors_response = validate_api_response(get_mentors(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await message.answer(str(e))
        return

    mentors = mentors_response.get("mentors", [])
    if not mentors:
        await message.answer("Список менторов пока пуст. Попробуйте позже.")
        return

    keyboard = InlineKeyboardBuilder()
    for mentor in mentors:
        keyboard.button(text=format_mentor(mentor), callback_data=f"mentor:{mentor['id']}")
    keyboard.adjust(1)

    await message.answer("Выберите ментора:", reply_markup=keyboard.as_markup())
    await state.set_state(SendPostcard.choosing_mentor)


@send_router.callback_query(F.data.startswith("mentor:"))
async def select_mentor(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    mentor_id = int(callback.data.split(":")[1])
    try:
        mentors_response = validate_api_response(get_mentors(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    mentor = next((m for m in mentors_response.get("mentors", []) if m["id"] == mentor_id), None)

    if not mentor:
        await callback.message.answer("Ментор не найден.")
        return

    await state.update_data(
        selected_mentor_id=mentor_id,
        selected_mentor_name=mentor["name"]["first"]
    )

    try:
        postcards_response = validate_api_response(get_postcards(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    postcards = postcards_response.get("postcards", [])
    unique_types = list({postcard["name_ru"] for postcard in postcards})
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
        postcards_response = validate_api_response(get_postcards(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    filtered_postcards = [
        postcard for postcard in postcards_response.get("postcards", [])
        if postcard["name_ru"] == selected_type
    ]

    if not filtered_postcards:
        await callback.message.answer("Нет открыток для выбранного типа.")
        return

    await callback.message.answer("Выберите открытку:")
    for postcard in filtered_postcards:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text=f"Выбрать открытку (ID: {postcard['id']})",
            callback_data=f"postcard:{postcard['id']}"
        )
        keyboard.adjust(1)
        await callback.message.answer(postcard["body"], reply_markup=keyboard.as_markup())

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
        postcards_response = validate_api_response(get_postcards(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    selected_postcard = next((postcard for postcard in postcards_response.get("postcards", []) if postcard["id"] == postcard_id), None)

    if not selected_postcard:
        await callback.message.answer("Выбранная открытка не найдена")
        return

    postcard_text = selected_postcard["body"].replace("#name", selected_mentor_name)
    confirming_message = (
        f"Вы выбрали открытку типа *{selected_type}*\n\n"
        f"Текст открытки:\n\n{postcard_text}\n\n"
        "Укажите, отправлять ли с указанием вашего имени?"
    )
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Да, указать отправителя", callback_data="send_with_sender")
    keyboard.button(text="Нет, без отправителя", callback_data="send_without_sender")
    keyboard.adjust(1)

    await callback.message.answer(confirming_message, parse_mode="Markdown", reply_markup=keyboard.as_markup())
    await state.set_state(SendPostcard.confirming)


async def send_postcard_to_mentor(callback: CallbackQuery, state: FSMContext, add_sender: bool):
    await callback.answer()
    data = await state.get_data()
    selected_mentor_id = data.get("selected_mentor_id")
    selected_postcard_id = data.get("selected_postcard_id")
    selected_mentor_name = data.get("selected_mentor_name", "Ментор")

    try:
        mentors_response = validate_api_response(get_mentors(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    try:
        postcards_response = validate_api_response(get_postcards(BASE_URL, SCHEMA_FILE), "🚨 Ошибка подключения к серверу.\n🔄 Попробуйте позже!")
    except ValueError as e:
        await callback.message.answer(str(e))
        return

    selected_mentor = next((mentor for mentor in mentors_response.get("mentors", []) if mentor["id"] == selected_mentor_id), None)

    selected_postcard = next((postcard for postcard in postcards_response.get("postcards", []) if postcard["id"] == selected_postcard_id), None)

    if not selected_mentor or not selected_postcard:
        await callback.message.answer("Выбранные ментор или открытка не найдены.")
        await state.clear()
        return

    postcard_body = selected_postcard["body"].replace("#name", selected_mentor_name)

    if add_sender:
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
    await send_postcard_to_mentor(callback, state, add_sender=True)


@send_router.callback_query(F.data == "send_without_sender")
async def send_without_sender(callback: CallbackQuery, state: FSMContext):
    await send_postcard_to_mentor(callback, state, add_sender=False)
