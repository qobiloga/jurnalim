from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .emaktab.parsers import SchoolClass
from .formatting import ACTION_TEXT as ACTION_LABELS, STATUS_ICONS

BTN_LOGIN = "🔑 eMaktab'ga kirish"
BTN_TODAY = "🗓 Bugungi darslarim"
BTN_WEEK = "📅 Haftalik jadvalim"
BTN_CLASSES = "📚 Sinflarim"
BTN_PROFILE = "👤 Profil"
BTN_STATUS = "✏️ Maqom berish"
BTN_LOGOUT = "🚪 Chiqish"


class WeekCb(CallbackData, prefix="tw"):
    offset: int


class ClassCb(CallbackData, prefix="cl"):
    group_id: str
    action: str  # list | menu | week | hw | sb
    offset: int = 0


class SummativeCb(CallbackData, prefix="sb"):
    group_id: str
    subject_id: str
    quarter: int = 0  # 0: ask for the quarter


class CaptchaCb(CallbackData, prefix="cap"):
    pass


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TODAY), KeyboardButton(text=BTN_WEEK)],
            [KeyboardButton(text=BTN_CLASSES), KeyboardButton(text=BTN_STATUS)],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_LOGOUT)],
        ],
        resize_keyboard=True,
    )


def login_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_LOGIN)]], resize_keyboard=True)


def week_nav_kb(offset: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Oldingi", callback_data=WeekCb(offset=offset - 1))
    if offset:
        b.button(text="🔄 Joriy hafta", callback_data=WeekCb(offset=0))
    b.button(text="Keyingi ▶️", callback_data=WeekCb(offset=offset + 1))
    return b.as_markup()


def classes_kb(classes: list[SchoolClass]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in classes:
        b.button(text=f"👥 {c.name}", callback_data=ClassCb(group_id=c.group_id, action="menu"))
    b.adjust(3)
    return b.as_markup()


def class_menu_kb(group_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 Dars jadvali", callback_data=ClassCb(group_id=group_id, action="week"))
    b.button(text="📝 Uy vazifalari", callback_data=ClassCb(group_id=group_id, action="hw"))
    b.button(text="📊 BSB / ChSB", callback_data=ClassCb(group_id=group_id, action="sb"))
    b.button(text="⬅️ Sinflar", callback_data=ClassCb(group_id="-", action="list"))
    b.adjust(2, 1, 1)
    return b.as_markup()


def class_week_kb(group_id: str, offset: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️", callback_data=ClassCb(group_id=group_id, action="week", offset=offset - 1))
    b.button(text="🔄 Joriy", callback_data=ClassCb(group_id=group_id, action="week", offset=0))
    b.button(text="▶️", callback_data=ClassCb(group_id=group_id, action="week", offset=offset + 1))
    b.button(text="⬅️ Sinf menyusi", callback_data=ClassCb(group_id=group_id, action="menu"))
    b.adjust(3, 1)
    return b.as_markup()


def back_to_class_kb(group_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Sinf menyusi", callback_data=ClassCb(group_id=group_id, action="menu"))
    return b.as_markup()


def captcha_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔄 Boshqa rasm", callback_data=CaptchaCb())
    return b.as_markup()


def summative_subjects_kb(group_id: str, subjects: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for sid, name in subjects:
        b.button(text=name, callback_data=SummativeCb(group_id=group_id, subject_id=sid))
    b.button(text="⬅️ Sinf menyusi", callback_data=ClassCb(group_id=group_id, action="menu"))
    b.adjust(*([2] * (len(subjects) // 2) + [1] * (len(subjects) % 2)), 1)
    return b.as_markup()


def summative_quarters_kb(group_id: str, subject_id: str, current: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for q in range(1, 5):
        b.button(text=f"{'✅ ' if q == current else ''}{q}-chorak",
                 callback_data=SummativeCb(group_id=group_id, subject_id=subject_id, quarter=q))
    b.button(text="⬅️ Fanlar", callback_data=ClassCb(group_id=group_id, action="sb"))
    b.button(text="🏫 Sinf menyusi", callback_data=ClassCb(group_id=group_id, action="menu"))
    b.adjust(4, 2)
    return b.as_markup()


# ---- Maqom berish (homework status) section ----
# emaktab ids are 13–19 digits; base36 keeps three of them inside Telegram's 64-byte callback limit
def b36(n: str) -> str:
    v, out = int(n), ""
    while True:
        v, r = divmod(v, 36)
        out = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + out
        if not v:
            return out


def unb36(s: str) -> str:
    return str(int(s, 36)) if s else ""


class StatusCb(CallbackData, prefix="mq"):
    step: str        # cls | hw | stu | act | do | list
    g: str = ""      # group id (base36)
    w: str = ""      # work id (base36)
    p: str = ""      # person id (base36)
    a: str = ""      # action: close | reopen | stop | cancel




def status_classes_kb(classes: list[SchoolClass]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in classes:
        b.button(text=f"👥 {c.name}", callback_data=StatusCb(step="cls", g=b36(c.group_id)))
    b.adjust(3)
    return b.as_markup()


def status_homework_kb(group_id: str, items: list) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, h in enumerate(items, 1):
        label = f"{i}. {h.subject} · {h.text}"
        b.button(text=label[:48], callback_data=StatusCb(step="hw", g=b36(group_id), w=b36(h.work_id)))
    b.button(text="⬅️ Sinflar", callback_data=StatusCb(step="list"))
    b.adjust(1)
    return b.as_markup()


def status_students_kb(group_id: str, work_id: str, students: list, short) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for st in students:
        b.button(text=f"{STATUS_ICONS.get(st.code, '🔘')} {short(st.name)}",
                 callback_data=StatusCb(step="stu", g=b36(group_id), w=b36(work_id), p=b36(st.person_id)))
    b.button(text="👥 Hammaga maqom berish", callback_data=StatusCb(step="all", g=b36(group_id), w=b36(work_id)))
    b.button(text="⬅️ Vazifalar", callback_data=StatusCb(step="cls", g=b36(group_id)))
    b.adjust(*([2] * (len(students) // 2) + [1] * (len(students) % 2)), 1, 1)
    return b.as_markup()


def status_actions_kb(group_id: str, work_id: str, person_id: str, actions: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for a in actions:
        b.button(text=ACTION_LABELS[a],
                 callback_data=StatusCb(step="act", g=b36(group_id), w=b36(work_id), p=b36(person_id), a=a))
    b.button(text="⬅️ O‘quvchilar", callback_data=StatusCb(step="hw", g=b36(group_id), w=b36(work_id)))
    b.adjust(1)
    return b.as_markup()


def status_confirm_kb(group_id: str, work_id: str, person_id: str, action: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    ids = dict(g=b36(group_id), w=b36(work_id), p=b36(person_id))
    b.button(text="✅ Tasdiqlash", callback_data=StatusCb(step="do", a=action, **ids))
    b.button(text="❌ Bekor", callback_data=StatusCb(step="stu", **ids))
    b.adjust(2)
    return b.as_markup()


BULK_LABELS = {"close": "✅ Hammasini tekshirish va yopish", "reopen": "🔁 Hammasini qayta ko‘rib chiqishga",
               "cancel": "🚫 Hammasini bekor qilish"}


def status_bulk_kb(group_id: str, work_id: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    ids = dict(g=b36(group_id), w=b36(work_id))
    for bulk, n in counts.items():
        if n:
            b.button(text=f"{BULK_LABELS[bulk]} ({n})", callback_data=StatusCb(step="allc", a=bulk, **ids))
    b.button(text="⬅️ O‘quvchilar", callback_data=StatusCb(step="hw", **ids))
    b.adjust(1)
    return b.as_markup()


def status_bulk_confirm_kb(group_id: str, work_id: str, bulk: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    ids = dict(g=b36(group_id), w=b36(work_id))
    b.button(text="✅ Tasdiqlash", callback_data=StatusCb(step="alldo", a=bulk, **ids))
    b.button(text="❌ Bekor", callback_data=StatusCb(step="all", **ids))
    b.adjust(2)
    return b.as_markup()
