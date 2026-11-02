from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .. import db

router = Router()


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.message(CommandStart())
async def start(message: Message) -> None:
    user = message.from_user
    await db.upsert_user(user.id, user.username, user.full_name)
    await message.answer(f"📓 <b>Jurnalim</b> botiga xush kelibsiz, {user.first_name}!")
