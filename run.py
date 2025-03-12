import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from bot.start_handler import start_router
from bot.send_handler import send_router
from bot.postcards_handler import view_postcards_router


async def main():
    load_dotenv()
    bot = Bot(token=os.getenv("TG_TOKEN"))
    dp = Dispatcher()
    dp.include_routers(start_router, send_router, view_postcards_router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
