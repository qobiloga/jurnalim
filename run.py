import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src import db
from src.config import ADMIN_IDS, BOT_TOKEN, ENCRYPTION_KEY, OPEN_TO_ALL
from src.handlers import auth, fallback, guest, menu, start, status


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # its INFO lines would log every emaktab URL
    if not BOT_TOKEN or not ENCRYPTION_KEY:
        raise SystemExit("Set BOT_TOKEN and ENCRYPTION_KEY in .env")

    await db.init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Closed mode (OPEN_TO_ALL=0): the real routers see admins only, everyone else falls through to guest.
    # fallback goes last among them, so it only gets messages no other handler took.
    for r in (start.router, auth.router, menu.router, status.router, fallback.router):
        if not OPEN_TO_ALL:
            r.message.filter(F.from_user.id.in_(ADMIN_IDS))
            r.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))
        dp.include_router(r)
    if not OPEN_TO_ALL:
        dp.include_router(guest.router)
    logging.info("bot is %s", "open to everyone" if OPEN_TO_ALL else f"admin-only ({len(ADMIN_IDS)} admins)")

    await bot.set_my_commands([
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="login", description="eMaktab'ga kirish"),
        BotCommand(command="chiqish", description="Akkauntni botdan o‘chirish"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
