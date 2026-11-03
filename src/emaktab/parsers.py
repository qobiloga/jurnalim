"""HTML → plain data for the emaktab pages the bot shows."""
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

TIME_RE = re.compile(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}")
CELL_RE = re.compile(r"^d(\d{8})_(\d+)$")


@dataclass
class SchoolClass:
    name: str
    group_id: str


@dataclass
class Lesson:
    day: date
    number: int
    subject: str
    time: str = ""
    room: str = ""
    teacher: str = ""
    class_name: str = ""


@dataclass
class Homework:
    text: str
    subject: str
    class_name: str
    lesson: str
    status: str


@dataclass
class SummativeRow:
    """One student's line of the "Sinf bo'yicha BSB/CHSB detalizatsiyasi" report."""
    name: str
    bsb: str = ""          # "43/50"
    bsb_pct: str = ""      # "86%"
    chsb: str = ""
    chsb_pct: str = ""
    score: str = ""        # quarter result in points
    grade: str = ""        # quarter grade 2..5


@dataclass
class SummativeReport:
    rows: list[SummativeRow] = field(default_factory=list)
    avg_bsb_pct: str = ""
    avg_chsb_pct: str = ""


@dataclass
class TeacherInfo:
    full_name: str
    teacher_id: str
    school_id: str
    school_name: str
    classes: list[SchoolClass] = field(default_factory=list)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _clean(s: str) -> str:
    return " ".join(s.split())


def _query(url: str, key: str) -> str:
    return parse_qs(urlparse(url).query).get(key, [""])[0]


def _cell_day(td_id: str) -> tuple[date, int] | None:
    m = CELL_RE.match(td_id or "")
    if not m:
        return None
    d = m.group(1)
    return date(int(d[:4]), int(d[4:6]), int(d[6:])), int(m.group(2))


def parse_my_classes(html: str) -> list[SchoolClass]:
    """/v2/myclasses: every class link points to /v2/class?class=<id>."""
    seen, out = set(), []
    content = _soup(html).find(id="content")
    for a in content.find_all("a", href=True) if content else []:
        if "/v2/class?" not in a["href"]:
            continue
        gid = _query(a["href"], "class")
        if gid and gid not in seen:
            seen.add(gid)
            out.append(SchoolClass(_clean(a.get_text()), gid))
    return out


def parse_school_id(html: str) -> str:
    content = _soup(html).find(id="content")
    for a in content.find_all("a", href=True) if content else []:
        if sid := _query(a["href"], "school"):
            return sid
    return ""


def parse_teacher_select(html: str) -> tuple[str, str]:
    """Teachers tab of /v2/schedules preselects the logged-in teacher: (id, full name)."""
    sel = _soup(html).find("select", attrs={"name": "teacher"})
    opt = sel.find("option", selected=True) if sel else None
    return (opt.get("value", ""), _clean(opt.get_text())) if opt else ("", "")


def parse_school_name(html: str) -> str:
    a = _soup(html).select_one("ul.old-site-crumbs a, #content a[href*='/v2/school?school=']")
    return _clean(a.get_text()) if a else ""


def parse_teacher_week(html: str) -> list[Lesson]:
    """Teachers tab of /v2/schedules: table.scheduleStaff, cells id=d<YYYYMMDD>_<n>."""
    out = []
    table = _soup(html).find("table", class_="scheduleStaff")
    for td in table.find_all("td", id=CELL_RE) if table else []:
        day, number = _cell_day(td["id"])
        for li in td.find_all("li", attrs={"data-lessonid": True}):
            subject = li.find("a", class_="aL")
            cls = li.select_one("p a.orange")
            ps = li.find_all("p", recursive=False)
            time = TIME_RE.search(li.get_text(" "))
            out.append(Lesson(
                day=day,
                number=number,
                subject=_clean(subject.get_text()).replace("...", "…") if subject else "",
                time=_clean(time.group(0)) if time else "",
                room=_clean(ps[-1].get_text()) if len(ps) > 1 else "",
                class_name=_clean(cls.get_text()) if cls else "",
            ))
    return sorted(out, key=lambda x: (x.day, x.number))


def parse_class_week(html: str) -> list[Lesson]:
    """/v2/schedules/view?group=…: table#editor, one div.dL per lesson."""
    out = []
    table = _soup(html).find("table", id="editor")
    for td in table.find_all("td", id=CELL_RE) if table else []:
        day, number = _cell_day(td["id"])
        for div in td.find_all("div", class_="dL"):
            subject = div.find("a", class_="aL")
            teacher = div.find("p", attrs={"data-test-id": "teacher"})
            time = div.find("p", attrs={"data-test-id": "time"})
            room = div.find("p", attrs={"data-test-id": "room"})
            out.append(Lesson(
                day=day,
                number=number,
                subject=(subject.get("title") or _clean(subject.get_text())) if subject else "",
                time=_clean(time.get_text()) if time else "",
                room=_clean(room.get_text()) if room else "",
                teacher=_clean(teacher.get_text()) if teacher else "",
            ))
    return sorted(out, key=lambda x: (x.day, x.number))


def parse_homework(html: str) -> tuple[int, list[Homework]]:
    """/v2/homework?view=List: table.hmw, columns: text, subject, class, lesson, report, status."""
    soup = _soup(html)
    found = soup.find("p", class_="found")
    total = int(re.sub(r"\D", "", found.get_text()) or 0) if found else 0
    out = []
    table = soup.find("table", class_="hmw")
    for tr in table.find_all("tr")[1:] if table else []:
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue
        out.append(Homework(
            text=_clean(tds[0].get_text()),
            subject=_clean(tds[1].get_text()),
            class_name=_clean(tds[2].get_text()),
            lesson=_clean(tds[3].get_text(" ")),
            status=_clean(tds[5].get_text()),
        ))
    return total, out


def parse_report_subjects(html: str) -> list[tuple[str, str]]:
    """Subjects offered for the chosen class on a report page: [(id, name)], without the placeholder."""
    sel = _soup(html).find("select", attrs={"name": "subject"})
    opts = sel.find_all("option") if sel else []
    return [(o.get("value", ""), _clean(o.get_text())) for o in opts if o.get("value") not in (None, "", "0")]


def parse_summative(html: str) -> SummativeReport:
    """Result HTML of the BSB/CHSB report: one row per student, then "O'rtacha ball" and "Foiz" rows.

    Columns are found by header text, because the number of BSB-n / CHSB-n columns varies.
    """
    table = _soup(html).find("table")
    report = SummativeReport()
    if not table:
        return report
    trs = table.find_all("tr")
    heads = [_clean(th.get_text()).lower() for th in trs[0].find_all(["th", "td"])]

    def col(*keys: str) -> int | None:
        return next((i for i, h in enumerate(heads) if all(k in h for k in keys)), None)

    i_bsb, i_bsb_pct = col("bsb", "jami"), col("bsb", "foiz")
    i_chsb, i_chsb_pct = col("chsb", "jami"), col("chsb", "foiz")
    # Two "Chorak uchun yakuniy" columns: points, then the grade
    final = [i for i, h in enumerate(heads) if "yakun" in h]
    i_score = final[0] if len(final) >= 2 else None
    i_grade = final[-1] if final else None

    for tr in trs[1:]:
        cells = [_clean(td.get_text()) for td in tr.find_all(["td", "th"])]
        get = lambda i: cells[i].replace("—", "").strip() if i is not None and i < len(cells) else ""  # noqa: E731
        name = cells[1] if len(cells) > 1 else ""
        if not cells or not name:
            continue
        low = name.lower()
        if "o‘rtacha" in low or "oʻrtacha" in low or "o'rtacha" in low:
            report.avg_bsb_pct, report.avg_chsb_pct = get(i_bsb_pct), get(i_chsb_pct)
            continue
        if low == "foiz":
            continue
        report.rows.append(SummativeRow(name, get(i_bsb), get(i_bsb_pct), get(i_chsb), get(i_chsb_pct),
                                        get(i_score), get(i_grade)))
    return report
