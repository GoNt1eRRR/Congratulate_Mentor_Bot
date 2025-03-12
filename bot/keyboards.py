from aiogram.types import KeyboardButton,ReplyKeyboardMarkup

main_keyboard = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='Отправить Открытку')],
    [KeyboardButton(text="Виды Открыток")]
], resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню',
)
