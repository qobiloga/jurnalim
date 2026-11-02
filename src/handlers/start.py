from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from .. import db, session
from ..keyboards import login_kb, main_kb

router = Router()


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    await db.upsert_user(user.id, user.username, user.full_name)
    if await session.has_account(user.id):
        await message.answer(f"📓 <b>Jurnalim</b>\nXush kelibsiz, {user.first_name}!", reply_markup=main_kb())
    else:
        await message.answer(
            "📓 <b>Jurnalim</b> — eMaktab ma'lumotlaringiz Telegram'da.\n\n"
            "Boshlash uchun eMaktab login va parolingiz bilan kiring.\n"
            "<i>Parol shifrlangan holda saqlanadi, bot eMaktab'da hech narsani o‘zgartirmaydi.</i>",
            reply_markup=login_kb(),
        )
