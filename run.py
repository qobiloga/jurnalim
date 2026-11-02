import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src import db
from src.config import ADMIN_IDS, BOT_TOKEN, ENCRYPTION_KEY
from src.handlers import auth, guest, menu, start


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines would log every emaktab URL
    if not BOT_TOKEN or not ENCRYPTION_KEY:
        raise SystemExit("Set BOT_TOKEN and ENCRYPTION_KEY in .env")

    await db.init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Admin-only while testing: the real routers see admins, everyone else falls through to guest
    admin = F.from_user.id.in_(ADMIN_IDS)
    for r in (start.router, auth.router, menu.router):
        r.message.filter(admin)
        r.callback_query.filter(admin)
        dp.include_router(r)
    dp.include_router(guest.router)

    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="login", description="eMaktab'ga kirish"),
        BotCommand(command="chiqish", description="Akkauntni botdan o‘chirish"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
