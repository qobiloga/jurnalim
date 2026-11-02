"""Turn parsed emaktab data into Telegram HTML messages."""
import html
from datetime import date

from .emaktab.parsers import Homework, Lesson, TeacherInfo


def escape(s: str) -> str:
    return html.escape(s, quote=False)  # names like O'g'li stay readable

WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
LIMIT = 3900  # Telegram caps messages at 4096 characters


def day_title(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day} {MONTHS[d.month - 1]}"


def _lesson_line(x: Lesson) -> str:
    who = x.class_name or x.teacher
    parts = [f"<b>{x.number}.</b> {escape(x.subject)}"]
    if who:
        parts.append(f"— {escape(who)}")
    line = " ".join(parts)
    extra = " · ".join(p for p in (x.time, x.room) if p)
    return f"{line}\n    <i>{escape(extra)}</i>" if extra else line


def _clip(text: str) -> str:
    return text if len(text) <= LIMIT else text[:LIMIT] + "\n…"


def lessons_day(title: str, d: date, lessons: list[Lesson]) -> str:
    rows = [x for x in lessons if x.day == d]
    head = f"🗓 <b>{escape(title)}</b>\n{day_title(d)}\n"
    if not rows:
        return head + "\nBu kunga dars yo‘q."
    return _clip(head + "\n" + "\n".join(_lesson_line(x) for x in rows))


def lessons_week(title: str, monday: date, lessons: list[Lesson]) -> str:
    sunday = date.fromordinal(monday.toordinal() + 6)
    out = [f"📅 <b>{escape(title)}</b>", f"{monday.day} {MONTHS[monday.month - 1]} — {sunday.day} {MONTHS[sunday.month - 1]}"]
    days = sorted({x.day for x in lessons})
    if not days:
        return "\n".join(out) + "\n\nBu haftaga dars yo‘q."
    for d in days:
        out.append(f"\n<b>{day_title(d)}</b>")
        out.extend(_lesson_line(x) for x in lessons if x.day == d)
    return _clip("\n".join(out))


def homework(class_name: str, total: int, items: list[Homework], shown: int = 10) -> str:
    out = [f"📝 <b>{escape(class_name)} — uy vazifalari</b> (jami {total})"]
    if not items:
        return out[0] + "\n\nUy vazifasi topilmadi."
    for h in items[:shown]:
        out.append(
            f"\n<b>{escape(h.subject)}</b> · {escape(h.lesson)}\n{escape(h.text)}\n<i>{escape(h.status)}</i>"
        )
    return _clip("\n".join(out))


def profile(t: TeacherInfo, login: str) -> str:
    classes = ", ".join(c.name for c in t.classes) or "—"
    return (
        f"👤 <b>{escape(t.full_name)}</b>\n"
        f"🏫 {escape(t.school_name)}\n"
        f"🔑 Login: <code>{escape(login)}</code>\n\n"
        f"📚 Sinflar ({len(t.classes)}): {escape(classes)}"
    )
