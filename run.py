import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src import db
from src.config import BOT_TOKEN
from src.handlers import start


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("Set BOT_TOKEN in .env")

    await db.init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)

    await bot.set_my_commands([BotCommand(command="start", description="Boshlash")])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
