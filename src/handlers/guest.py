"""Everyone who is not an admin: the bot is closed while it is being tested."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

router = Router()


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.message(F.chat.type == "private")
async def closed(message: Message) -> None:
    await message.answer("📓 <b>Jurnalim</b> hozircha test rejimida. Tez orada ochiladi!")


@router.callback_query()
async def closed_cb(call: CallbackQuery) -> None:
    await call.answer("Bot hozircha test rejimida.", show_alert=True)
