"""Last router: anything the other handlers did not take — point the user to the right next step."""
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from .. import session
from ..keyboards import login_kb, main_kb

router = Router()


@router.message(F.chat.type == "private")
async def unknown(message: Message) -> None:
    if await session.has_account(message.from_user.id):
        await message.answer("👇 Menyudan kerakli bo‘limni tanlang.", reply_markup=main_kb())
    else:
        await message.answer(
            "🔑 Avval eMaktab'ga kiring: pastdagi <b>“eMaktab'ga kirish”</b> tugmasini bosing,\n"
            "keyin login va parolingizni yozing.",
            reply_markup=login_kb(),
        )


@router.callback_query()
async def stale_button(call: CallbackQuery) -> None:
    await call.answer("Bu tugma eskirgan. /start ni bosing.", show_alert=True)
