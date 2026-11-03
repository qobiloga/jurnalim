"""✏️ Maqom berish: change a student's homework status on eMaktab — the bot's only write.

Class → homework → student → action → explicit confirmation. Every change re-reads the page,
is checked against the actions the page itself offers, and is written to the status_changes audit.
"""
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from .. import formatting, session
from ..emaktab.parsers import STATUS_ACTIONS
from ..formatting import _short_name
from ..keyboards import (
    BTN_STATUS,
    StatusCb,
    status_actions_kb,
    status_classes_kb,
    status_confirm_kb,
    status_homework_kb,
    status_students_kb,
    unb36,
)
from .menu import _edit, _guard

router = Router()
log = logging.getLogger(__name__)


@router.message(F.text == BTN_STATUS)
async def start(message: Message) -> None:
    t = await _guard(message, session.teacher(message.from_user.id))
    if t is not None:
        await message.answer(formatting.status_pick_class(), reply_markup=status_classes_kb(t.classes))


async def _show_detail(call: CallbackQuery, gid: str, wid: str, note: str = "", fresh: bool = False) -> None:
    tg_id = call.from_user.id
    t = await _guard(call.message, session.teacher(tg_id))
    detail = await _guard(call.message, session.homework_detail(tg_id, wid, fresh=fresh)) if t else None
    if detail is None:
        return
    _, items = await session.class_homework(tg_id, gid)
    hw = next((h for h in items if h.work_id == wid), None)
    name = next((c.name for c in t.classes if c.group_id == gid), "Sinf")
    await _edit(call.message, formatting.status_detail(name, hw, detail, note),
                reply_markup=status_students_kb(gid, wid, detail.students, _short_name))


@router.callback_query(StatusCb.filter())
async def step(call: CallbackQuery, callback_data: StatusCb) -> None:
    tg_id = call.from_user.id
    cb = callback_data
    gid, wid, pid = unb36(cb.g), unb36(cb.w), unb36(cb.p)
    t = await _guard(call.message, session.teacher(tg_id))
    if t is None:
        return await call.answer()
    name = next((c.name for c in t.classes if c.group_id == gid), "Sinf")

    if cb.step == "list":
        await _edit(call.message, formatting.status_pick_class(), reply_markup=status_classes_kb(t.classes))
    elif cb.step == "cls":
        result = await _guard(call.message, session.class_homework(tg_id, gid))
        if result is not None:
            total, items = result
            items = [h for h in items if h.work_id]
            await _edit(call.message, formatting.status_pick_homework(name, total, items),
                        reply_markup=status_homework_kb(gid, items))
    elif cb.step == "hw":
        await _show_detail(call, gid, wid)
    elif cb.step in ("stu", "act"):
        detail = await _guard(call.message, session.homework_detail(tg_id, wid))
        st = next((x for x in detail.students if x.person_id == pid), None) if detail else None
        if st is None:
            return await call.answer("O‘quvchi topilmadi", show_alert=True)
        actions = STATUS_ACTIONS.get(st.code, [])
        if cb.step == "stu":
            await _edit(call.message, formatting.status_student(name, st.name, st.label, st.code, bool(actions)),
                        reply_markup=status_actions_kb(gid, wid, pid, actions))
        else:
            _, items = await session.class_homework(tg_id, gid)
            hw = next((h for h in items if h.work_id == wid), None)
            await _edit(call.message, formatting.status_confirm(st.name, hw.text if hw else "", st.label, cb.a),
                        reply_markup=status_confirm_kb(gid, wid, pid, cb.a))
    elif cb.step == "do":
        await call.answer("⏳ Saqlanmoqda…")
        try:
            old, new = await session.change_status(tg_id, wid, pid, cb.a)
            note = f"✅ <b>Saqlandi:</b> {formatting.escape(old)} ➜ {formatting.escape(new)}"
        except session.StatusChangeError as e:
            note = f"❌ <b>O‘zgartirilmadi:</b> {formatting.escape(str(e))}"
        except Exception:
            log.exception("status change failed")
            note = "❌ <b>O‘zgartirilmadi:</b> eMaktab javob bermadi."
        await _show_detail(call, gid, wid, note, fresh=True)
        return
    await call.answer()
