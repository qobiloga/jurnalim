"""eMaktab login: login → password → (captcha if the site asks for one)."""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from .. import session
from ..emaktab.client import CaptchaRequired, LoginOk
from ..keyboards import BTN_LOGIN, BTN_LOGOUT, CaptchaCb, captcha_kb, login_kb, main_kb

router = Router()
log = logging.getLogger(__name__)


class Login(StatesGroup):
    login = State()
    password = State()
    captcha = State()


@router.message(F.text == BTN_LOGIN)
@router.message(Command("login"))
async def ask_login(message: Message, state: FSMContext) -> None:
    await state.set_state(Login.login)
    await message.answer("eMaktab <b>login</b>ingizni yozing:")


@router.message(Login.login, F.text)
async def got_login(message: Message, state: FSMContext) -> None:
    await state.update_data(login=message.text.strip())
    await state.set_state(Login.password)
    await message.answer("Endi <b>parol</b>ni yozing.\n<i>Xabar darhol chatdan o‘chiriladi.</i>")


@router.message(Login.password, F.text)
async def got_password(message: Message, state: FSMContext, bot: Bot) -> None:
    password = message.text
    try:
        await message.delete()
    except Exception:
        log.warning("could not delete password message")
    await state.update_data(password=password)
    await _attempt(message, state, bot)


@router.message(Login.captcha, F.text)
async def got_captcha(message: Message, state: FSMContext, bot: Bot) -> None:
    await _attempt(message, state, bot, captcha_answer=message.text.strip())


@router.callback_query(Login.captcha, CaptchaCb.filter())
async def refresh_captcha(call: CallbackQuery, state: FSMContext) -> None:
    result = await session.new_captcha(call.from_user.id)
    if not result:
        await state.clear()
        await call.message.answer("Captcha eskirdi, qaytadan kiring.", reply_markup=login_kb())
        return await call.answer()
    await state.update_data(captcha_id=result.captcha_id)
    await _send_captcha(call.message, result)
    await call.answer()


async def _send_captcha(message: Message, result: CaptchaRequired) -> None:
    caption = "❌ Rasmdagi belgilar noto‘g‘ri. Yangisini kiriting:" if result.wrong_answer else (
        "🔐 eMaktab tasdiqlash so‘radi. Rasmdagi belgilarni yozing:"
    )
    await message.answer_photo(
        BufferedInputFile(result.image, "captcha.png"), caption=caption, reply_markup=captcha_kb()
    )


async def _attempt(message: Message, state: FSMContext, bot: Bot, captcha_answer: str | None = None) -> None:
    data = await state.get_data()
    tg_id = message.chat.id
    wait = await message.answer("⏳ eMaktab'ga ulanilmoqda…")
    try:
        result = await session.try_login(
            tg_id, data["login"], data["password"], data.get("captcha_id"), captcha_answer
        )
    except session.Locked as e:
        await state.clear()
        await wait.edit_text(f"⛔ Ko‘p marta xato kiritildi. {e.minutes} daqiqadan keyin urinib ko‘ring.")
        return
    except Exception:
        log.exception("login failed")
        await state.clear()
        await wait.edit_text("⚠️ eMaktab javob bermadi. Birozdan keyin qayta urinib ko‘ring.")
        return

    if isinstance(result, LoginOk):
        await state.clear()
        await wait.delete()
        await message.answer("✅ eMaktab'ga muvaffaqiyatli kirdingiz!", reply_markup=main_kb())
    elif isinstance(result, CaptchaRequired):
        await state.set_state(Login.captcha)
        await state.update_data(captcha_id=result.captcha_id)
        await wait.delete()
        await _send_captcha(message, result)
    else:
        # Never retry a wrong password automatically — that is what triggers the captcha
        await state.clear()
        await wait.edit_text(f"❌ {result.message}\nQaytadan urinib ko‘ring.")
        await message.answer("Kirish uchun tugmani bosing.", reply_markup=login_kb())


@router.message(F.text == BTN_LOGOUT)
@router.message(Command("chiqish"))
async def do_logout(message: Message, state: FSMContext) -> None:
    await state.clear()
    await session.logout(message.from_user.id)
    await message.answer(
        "🚪 Akkaunt botdan o‘chirildi (login, parol va sessiya).", reply_markup=login_kb()
    )
