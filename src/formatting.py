"""Turn parsed emaktab data into Telegram HTML messages."""
import html
from datetime import date, datetime

from .emaktab.parsers import Homework, Lesson, SummativeReport, TeacherInfo

WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
NUMBERS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
LIMIT = 3900  # Telegram caps messages at 4096 characters

# Matched as lowercase substrings of the subject name, first hit wins
SUBJECT_ICONS = [
    ("informatika", "💻"), ("algebra", "➗"), ("geometriya", "📐"), ("matematika", "🔢"),
    ("fizika", "⚛️"), ("kimyo", "🧪"), ("biologiya", "🧬"), ("geografiya", "🌍"),
    ("tarix", "📜"), ("adabiyot", "📖"), ("ona tili", "✍️"), ("o‘zbek", "✍️"), ("o'zbek", "✍️"),
    ("ingliz", "🇬🇧"), ("rus", "🇷🇺"), ("nemis", "🇩🇪"), ("fransuz", "🇫🇷"),
    ("jismoniy", "⚽"), ("musiqa", "🎵"), ("tasviriy", "🎨"), ("texnolog", "🛠"),
    ("kelajak", "🚀"), ("chqbt", "🎖"), ("chaqiruv", "🎖"), ("tarbiya", "🤝"), ("huquq", "⚖️"),
    ("iqtisod", "💰"), ("astronomiya", "🔭"), ("chizmachilik", "📏"), ("odobnoma", "🌱"),
]


def escape(s: str) -> str:
    return html.escape(s, quote=False)  # names like O'g'li stay readable


def subject_icon(name: str) -> str:
    low = name.lower()
    return next((icon for key, icon in SUBJECT_ICONS if key in low), "📘")


def _num(n: int) -> str:
    return NUMBERS[n] if 0 <= n < len(NUMBERS) else f"<b>{n}.</b>"


def _date(d: date) -> str:
    return f"{d.day}-{MONTHS[d.month - 1]}"


def day_title(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {_date(d)}"


def _room(room: str) -> str:
    return "" if not room or "yo‘q" in room or "yo'q" in room else room


def _span(time: str) -> tuple[str, str] | None:
    parts = [p.strip() for p in time.split("-")]
    return (parts[0], parts[1]) if len(parts) == 2 else None


def _clip(text: str) -> str:
    return text if len(text) <= LIMIT else text[:LIMIT] + "\n…"


def _lesson_state(x: Lesson, now: datetime | None) -> str:
    """✅ finished · 🔴 in progress · '' otherwise (only for today's lessons)."""
    span = _span(x.time)
    if not now or not span or x.day != now.date():
        return ""
    t = now.strftime("%H:%M")
    if t >= span[1].zfill(5):
        return "✅"
    if t >= span[0].zfill(5):
        return "🔴"
    return ""


def _lesson_block(x: Lesson, now: datetime | None = None) -> str:
    state = _lesson_state(x, now)
    head = f"{_num(x.number)} {subject_icon(x.subject)} <b>{escape(x.subject)}</b>"
    if state == "🔴":
        head += "  🔴 <i>hozir</i>"
    elif state == "✅":
        head = f"<s>{head}</s> ✅"
    details = []
    if x.time:
        details.append(f"🕗 {escape(x.time.replace(' - ', '–'))}")
    if x.class_name:
        details.append(f"👥 {escape(x.class_name)}")
    if x.teacher:
        details.append(f"👤 {escape(x.teacher)}")
    if room := _room(x.room):
        details.append(f"🚪 {escape(room)}")
    return head + ("\n      " + "  ·  ".join(details) if details else "")


def _next_lesson(rows: list[Lesson], now: datetime) -> Lesson | None:
    t = now.strftime("%H:%M")
    return next((x for x in rows if (s := _span(x.time)) and s[0].zfill(5) > t), None)


def lessons_day(title: str, d: date, lessons: list[Lesson], now: datetime | None = None) -> str:
    rows = [x for x in lessons if x.day == d]
    head = f"🗓 <b>{escape(title)}</b>\n📆 {day_title(d)}"
    if not rows:
        return head + "\n\n🎉 Bugun dars yo‘q — dam oling!"
    out = [head + f"  ·  📚 {len(rows)} ta dars", ""]
    out.extend(_lesson_block(x, now) + "\n" for x in rows)
    if now and now.date() == d:
        nxt = _next_lesson(rows, now)
        if nxt:
            out.append(f"⏭ <b>Keyingi dars:</b> {escape(nxt.subject)} ({escape(nxt.class_name or nxt.teacher)}) — {nxt.time.split('-')[0].strip()}")
        elif all(_lesson_state(x, now) == "✅" for x in rows):
            out.append("🏁 <b>Bugungi darslar tugadi.</b> Yaxshi dam oling!")
    return _clip("\n".join(out).rstrip())


def lessons_week(title: str, monday: date, lessons: list[Lesson], today: date | None = None) -> str:
    sunday = date.fromordinal(monday.toordinal() + 6)
    head = f"📅 <b>{escape(title)}</b>\n🗓 {_date(monday)} — {_date(sunday)}  ·  📚 {len(lessons)} ta dars"
    days = sorted({x.day for x in lessons})
    if not days:
        return head + "\n\n📭 Bu haftaga dars kiritilmagan."
    out = [head]
    for d in days:
        mark = "  📍 <i>bugun</i>" if d == today else ""
        lines = []
        for x in (x for x in lessons if x.day == d):
            start = escape(x.time.split("-")[0].strip()) if x.time else ""
            who = escape(x.class_name or x.teacher)
            lines.append(
                f"{_num(x.number)} <code>{start}</code> {subject_icon(x.subject)} {escape(x.subject)}"
                + (f" — {who}" if who else "")
            )
        out.append(f"\n📌 <b>{day_title(d)}</b>{mark}\n<blockquote>" + "\n".join(lines) + "</blockquote>")
    return _clip("\n".join(out))


def _hw_status(status: str) -> str:
    low = status.lower()
    if "tugal" in low:
        return "✅"
    if "berilmagan" in low or "muddati" in low:
        return "⚠️"
    return "🕓"


def homework(class_name: str, total: int, items: list[Homework], shown: int = 10) -> str:
    head = f"📝 <b>Uy vazifalari</b>  ·  👥 {escape(class_name)}\n📊 Jami: <b>{total}</b> ta"
    if not items:
        return head + "\n\n📭 Uy vazifasi topilmadi."
    out = [head]
    for h in items[:shown]:
        out.append(
            f"\n{subject_icon(h.subject)} <b>{escape(h.subject)}</b>  {_hw_status(h.status)} <i>{escape(h.status)}</i>\n"
            f"<blockquote>📄 {escape(h.text)}</blockquote>"
            f"🗓 {escape(h.lesson)}"
        )
    if total > shown:
        out.append(f"\n<i>… va yana {total - shown} ta. To‘liq ro‘yxat eMaktab saytida.</i>")
    return _clip("\n".join(out))


def classes_title(count: int) -> str:
    return f"📚 <b>Sinflarim</b>\n👥 Jami: <b>{count}</b> ta sinf\n\n👇 Sinfni tanlang:"


def class_title(name: str) -> str:
    return f"🏫 <b>{escape(name)}</b> sinfi\n\n👇 Bo‘limni tanlang:"


def profile(t: TeacherInfo, login: str) -> str:
    classes = "  ".join(f"<code>{escape(c.name)}</code>" for c in t.classes) or "—"
    return (
        "👤 <b>Profil</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🧑‍🏫 <b>{escape(t.full_name)}</b>\n"
        f"🏫 Maktab: {escape(t.school_name)}\n"
        f"🔑 Login: <code>{escape(login)}</code>\n"
        f"🌐 Platforma: eMaktab.uz\n"
        "━━━━━━━━━━━━━━━\n"
        f"📚 <b>Sinflarim</b> ({len(t.classes)} ta):\n{classes}"
    )


GRADE_ICONS = {"5": "🟢", "4": "🔵", "3": "🟡", "2": "🔴"}


def _short_name(full: str) -> str:
    """"Abdixofizova Guzal Alisher Qizi" → "Abdixofizova G." — keeps 30+ rows readable on a phone."""
    parts = full.split()
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else full


def summative_pick_subject(class_name: str) -> str:
    return f"📊 <b>BSB / ChSB</b>  ·  👥 {escape(class_name)}\n\n👇 Fanni tanlang:"


def summative_pick_quarter(class_name: str, subject: str) -> str:
    return (f"📊 <b>BSB / ChSB</b>  ·  👥 {escape(class_name)}\n{subject_icon(subject)} {escape(subject)}\n\n"
            "👇 Chorakni tanlang:")


def summative(class_name: str, subject: str, quarter: int, r: SummativeReport) -> str:
    head = (f"📊 <b>BSB / ChSB</b>  ·  👥 {escape(class_name)}\n"
            f"{subject_icon(subject)} {escape(subject)}  ·  🗓 {quarter}-chorak")
    # A quarter that has not started yet comes back as every student with "0/0"
    started = any(x.grade or x.bsb not in ("", "0/0") or x.chsb not in ("", "0/0") for x in r.rows)
    if not started:
        return head + "\n\n📭 Bu chorak uchun BSB/ChSB natijalari hali kiritilmagan."
    counts = {g: sum(1 for x in r.rows if x.grade == g) for g in GRADE_ICONS}
    missing = sum(1 for x in r.rows if not x.grade)
    grades = "  ".join(f"{GRADE_ICONS[g]} {g} — <b>{n}</b>" for g, n in counts.items() if n)
    summary = [
        "━━━━━━━━━━━━━━━",
        f"📈 O‘rtacha: BSB <b>{escape(r.avg_bsb_pct or '—')}</b>  ·  ChSB <b>{escape(r.avg_chsb_pct or '—')}</b>",
        f"⭐ Chorak baholari:  {grades or '—'}",
    ]
    if missing:
        summary.append(f"⚪ Yakuniy bahosi yo‘q: <b>{missing}</b> ta o‘quvchi")
    summary.append("━━━━━━━━━━━━━━━")
    lines = []
    for i, x in enumerate(r.rows, 1):
        mark = f"{GRADE_ICONS.get(x.grade, '⚪')} <b>{escape(x.grade)}</b>" if x.grade else "⚪"
        lines.append(f"{i}. {escape(_short_name(x.name))} — BSB {escape(x.bsb or '—')} · ChSB {escape(x.chsb or '—')} → {mark}")
    # Long classes: cut the list (never inside a tag) so the message stays under Telegram's limit
    base = "\n".join([head, *summary]) + "\n<blockquote expandable></blockquote>"
    kept, size = [], len(base)
    for line in lines:
        if size + len(line) + 1 > LIMIT - 40:
            kept.append(f"… va yana {len(lines) - len(kept)} ta")
            break
        kept.append(line)
        size += len(line) + 1
    return "\n".join([head, *summary]) + "\n<blockquote expandable>" + "\n".join(kept) + "</blockquote>"
