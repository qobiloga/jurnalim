from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .emaktab.parsers import SchoolClass

BTN_LOGIN = "🔑 eMaktab'ga kirish"
BTN_TODAY = "🗓 Bugungi darslarim"
BTN_WEEK = "📅 Haftalik jadvalim"
BTN_CLASSES = "📚 Sinflarim"
BTN_PROFILE = "👤 Profil"
BTN_LOGOUT = "🚪 Chiqish"


class WeekCb(CallbackData, prefix="tw"):
    offset: int


class ClassCb(CallbackData, prefix="cl"):
    group_id: str
    action: str  # menu | week | hw
    offset: int = 0


class CaptchaCb(CallbackData, prefix="cap"):
    pass


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TODAY), KeyboardButton(text=BTN_WEEK)],
            [KeyboardButton(text=BTN_CLASSES), KeyboardButton(text=BTN_PROFILE)],
            [KeyboardButton(text=BTN_LOGOUT)],
        ],
        resize_keyboard=True,
    )


def login_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_LOGIN)]], resize_keyboard=True)


def week_nav_kb(offset: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Oldingi", callback_data=WeekCb(offset=offset - 1))
    if offset:
        b.button(text="Joriy hafta", callback_data=WeekCb(offset=0))
    b.button(text="Keyingi ▶️", callback_data=WeekCb(offset=offset + 1))
    return b.as_markup()


def classes_kb(classes: list[SchoolClass]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for c in classes:
        b.button(text=c.name, callback_data=ClassCb(group_id=c.group_id, action="menu"))
    b.adjust(4)
    return b.as_markup()


def class_menu_kb(group_id: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📅 Dars jadvali", callback_data=ClassCb(group_id=group_id, action="week"))
    b.button(text="📝 Uy vazifalari", callback_data=ClassCb(group_id=group_id, action="hw"))
    b.button(text="⬅️ Sinflar", callback_data=ClassCb(group_id="-", action="list"))
    b.adjust(2, 1)
    return b.as_markup()


def class_week_kb(group_id: str, offset: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️", callback_data=ClassCb(group_id=group_id, action="week", offset=offset - 1))
    b.button(text="Joriy", callback_data=ClassCb(group_id=group_id, action="week", offset=0))
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
