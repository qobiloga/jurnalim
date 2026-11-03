"""Read-only menus over the logged-in teacher's emaktab data."""
import logging
from contextlib import suppress
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from .. import db, formatting, session
from ..config import TIMEZONE
from ..keyboards import (
    BTN_CLASSES,
    BTN_PROFILE,
    BTN_TODAY,
    BTN_WEEK,
    ClassCb,
    SummativeCb,
    WeekCb,
    back_to_class_kb,
    class_menu_kb,
    class_week_kb,
    classes_kb,
    login_kb,
    summative_quarters_kb,
    summative_subjects_kb,
    week_nav_kb,
)

router = Router()
log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)


def _today() -> date:
    return _now().date()


async def _edit(message: Message, text: str, **kwargs) -> None:
    # Pressing the button for the view already shown would raise "message is not modified"
    with suppress(TelegramBadRequest):
        await message.edit_text(text, **kwargs)


def _monday(offset: int) -> date:
    t = _today()
    return t - timedelta(days=t.weekday()) + timedelta(weeks=offset)


async def _guard(message: Message, coro):
    """Run an emaktab call and turn its failures into user-facing messages."""
    try:
        return await coro
    except session.NeedsLogin:
        await message.answer("🔑 eMaktab'ga qaytadan kirish kerak.", reply_markup=login_kb())
    except session.Locked as e:
        await message.answer(f"⛔ {e.minutes} daqiqadan keyin urinib ko‘ring.")
    except session.NotTeacher:
        await message.answer(
            "👩‍🏫 Hozircha Jurnalim faqat <b>o‘qituvchi</b> akkauntlari uchun ishlaydi.\n"
            "O‘quvchi va ota-onalar uchun bo‘limlar tez orada qo‘shiladi."
        )
    except Exception:
        log.exception("emaktab request failed")
        await message.answer("⚠️ eMaktab javob bermadi. Birozdan keyin qayta urinib ko‘ring.")
    return None


@router.message(F.text == BTN_TODAY)
async def today(message: Message) -> None:
    d = _today()
    lessons = await _guard(message, session.teacher_week(message.from_user.id, d))
    if lessons is not None:
        await message.answer(formatting.lessons_day("Bugungi darslarim", d, lessons, _now()))


@router.message(F.text == BTN_WEEK)
async def week(message: Message) -> None:
    lessons = await _guard(message, session.teacher_week(message.from_user.id, _monday(0)))
    if lessons is not None:
        await message.answer(
            formatting.lessons_week("Haftalik jadvalim", _monday(0), lessons, _today()), reply_markup=week_nav_kb(0)
        )


@router.callback_query(WeekCb.filter())
async def week_nav(call: CallbackQuery, callback_data: WeekCb) -> None:
    monday = _monday(callback_data.offset)
    lessons = await _guard(call.message, session.teacher_week(call.from_user.id, monday))
    if lessons is not None:
        await _edit(
            call.message,
            formatting.lessons_week("Haftalik jadvalim", monday, lessons, _today()),
            reply_markup=week_nav_kb(callback_data.offset),
        )
    await call.answer()


@router.message(F.text == BTN_CLASSES)
async def classes(message: Message) -> None:
    t = await _guard(message, session.teacher(message.from_user.id))
    if t is not None:
        await message.answer(formatting.classes_title(len(t.classes)), reply_markup=classes_kb(t.classes))


@router.callback_query(ClassCb.filter())
async def class_action(call: CallbackQuery, callback_data: ClassCb) -> None:
    tg_id = call.from_user.id
    t = await _guard(call.message, session.teacher(tg_id))
    if t is None:
        return await call.answer()
    gid = callback_data.group_id
    name = next((c.name for c in t.classes if c.group_id == gid), "Sinf")

    if callback_data.action == "list":
        await _edit(call.message, formatting.classes_title(len(t.classes)), reply_markup=classes_kb(t.classes))
    elif callback_data.action == "menu":
        await _edit(call.message, formatting.class_title(name), reply_markup=class_menu_kb(gid))
    elif callback_data.action == "week":
        monday = _monday(callback_data.offset)
        lessons = await _guard(call.message, session.class_week(tg_id, gid, monday))
        if lessons is not None:
            await _edit(
                call.message,
                formatting.lessons_week(f"{name} — dars jadvali", monday, lessons, _today()),
                reply_markup=class_week_kb(gid, callback_data.offset),
            )
    elif callback_data.action == "hw":
        result = await _guard(call.message, session.class_homework(tg_id, gid))
        if result is not None:
            await _edit(call.message, formatting.homework(name, *result), reply_markup=back_to_class_kb(gid))
    elif callback_data.action == "sb":
        subjects = await _guard(call.message, session.summative_subjects(tg_id, gid))
        if subjects is not None:
            if subjects:
                await _edit(call.message, formatting.summative_pick_subject(name),
                            reply_markup=summative_subjects_kb(gid, subjects))
            else:
                await _edit(call.message, f"📊 {formatting.escape(name)}: BSB/ChSB uchun fan topilmadi.",
                            reply_markup=back_to_class_kb(gid))
    await call.answer()


@router.callback_query(SummativeCb.filter())
async def summative(call: CallbackQuery, callback_data: SummativeCb) -> None:
    tg_id, gid, sid, q = call.from_user.id, callback_data.group_id, callback_data.subject_id, callback_data.quarter
    t = await _guard(call.message, session.teacher(tg_id))
    subjects = await _guard(call.message, session.summative_subjects(tg_id, gid)) if t else None
    if t is None or subjects is None:
        return await call.answer()
    name = next((c.name for c in t.classes if c.group_id == gid), "Sinf")
    subject = next((n for i, n in subjects if i == sid), "Fan")
    if not q:
        await _edit(call.message, formatting.summative_pick_quarter(name, subject),
                    reply_markup=summative_quarters_kb(gid, sid))
        return await call.answer()
    await call.answer("⏳ Hisobot tayyorlanmoqda…")
    await _edit(call.message, f"⏳ <b>{formatting.escape(name)}</b> · {formatting.escape(subject)} · {q}-chorak\n"
                              "eMaktab'da hisobot tayyorlanmoqda, bir necha soniya kuting…")
    report = await _guard(call.message, session.summative(tg_id, gid, sid, q))
    if report is not None:
        await _edit(call.message, formatting.summative(name, subject, q, report),
                    reply_markup=summative_quarters_kb(gid, sid, q))


@router.message(F.text == BTN_PROFILE)
async def profile(message: Message) -> None:
    t = await _guard(message, session.teacher(message.from_user.id))
    if t is not None:
        acc = await db.get_account(message.from_user.id)
        await message.answer(formatting.profile(t, acc["login"] if acc else ""))
