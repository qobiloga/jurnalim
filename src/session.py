"""Per-user emaktab sessions: login, cookie persistence, transparent re-login and page cache."""
import asyncio
import json
import logging
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from . import crypto, db
from .config import CACHE_SECONDS, LOGIN_LOCK_MINUTES, MAX_FAILED_LOGINS, TIMEZONE
from .emaktab import parsers
from .emaktab.client import CaptchaRequired, EmaktabClient, LoginOk, LoginResult, SessionExpired, WrongCredentials

log = logging.getLogger(__name__)
BASE = "https://schools.emaktab.uz/v2"


class NeedsLogin(Exception):
    """No saved account, or the saved password no longer works — the user must log in again."""


class Locked(Exception):
    def __init__(self, minutes: int) -> None:
        self.minutes = minutes


class NotTeacher(Exception):
    """The account has no teacher pages (student/parent): the menus are built for teachers only."""


class _Session:
    def __init__(self, client: EmaktabClient) -> None:
        self.client = client
        self.lock = asyncio.Lock()
        self.cache: dict[str, tuple[float, object]] = {}  # page HTML by URL, parsed reports by key
        self.teacher: parsers.TeacherInfo | None = None


_sessions: dict[int, _Session] = {}
# Clients waiting for a captcha answer: the captcha is bound to that client's cookies
_pending: dict[int, EmaktabClient] = {}


async def _drop(tg_id: int) -> None:
    for store in (_sessions, _pending):
        obj = store.pop(tg_id, None)
        if obj is not None:
            await (obj.client if isinstance(obj, _Session) else obj).close()


async def _check_lock(tg_id: int) -> None:
    _, locked_until = await db.get_lock(tg_id)
    if locked_until:
        left = datetime.fromisoformat(locked_until) - datetime.now()
        if left.total_seconds() > 0:
            raise Locked(int(left.total_seconds() // 60) + 1)


async def try_login(
    tg_id: int, login: str, password: str, captcha_id: str | None = None, captcha_answer: str | None = None
) -> LoginResult:
    await _check_lock(tg_id)
    client = _pending.pop(tg_id, None) if captcha_answer else None
    client = client or EmaktabClient()
    try:
        result = await client.login(login, password, captcha_id, captcha_answer)
    except Exception:
        await client.close()
        raise

    if isinstance(result, LoginOk):
        await _drop(tg_id)
        await db.save_account(
            tg_id, login, crypto.encrypt(password), crypto.encrypt(json.dumps(client.export_cookies()))
        )
        await db.set_lock(tg_id, 0, None)
        _sessions[tg_id] = _Session(client)
    elif isinstance(result, CaptchaRequired):
        _pending[tg_id] = client
    else:
        await client.close()
        failed, _ = await db.get_lock(tg_id)
        failed += 1
        until = None
        if failed >= MAX_FAILED_LOGINS:
            until = (datetime.now() + timedelta(minutes=LOGIN_LOCK_MINUTES)).isoformat(timespec="seconds")
            failed = 0
        await db.set_lock(tg_id, failed, until)
    return result


async def new_captcha(tg_id: int) -> CaptchaRequired | None:
    client = _pending.get(tg_id)
    # Fresh id + image on the same client, exactly what the site's refresh button does
    return await client.new_captcha() if client else None


async def logout(tg_id: int) -> None:
    """Forget the account locally. Nothing is sent to emaktab."""
    await _drop(tg_id)
    await db.delete_account(tg_id)


async def has_account(tg_id: int) -> bool:
    return await db.get_account(tg_id) is not None


async def _session(tg_id: int) -> _Session:
    if tg_id in _sessions:
        return _sessions[tg_id]
    acc = await db.get_account(tg_id)
    if not acc:
        raise NeedsLogin()
    cookies = json.loads(crypto.decrypt(acc["cookies_enc"])) if acc["cookies_enc"] else []
    s = _sessions[tg_id] = _Session(EmaktabClient(cookies))
    return s


async def _relogin(tg_id: int, s: _Session) -> None:
    """Session cookies expired: log in once with the stored password, never retry on failure."""
    acc = await db.get_account(tg_id)
    if not acc:
        raise NeedsLogin()
    await _check_lock(tg_id)
    result = await s.client.login(acc["login"], crypto.decrypt(acc["password_enc"]))
    if not isinstance(result, LoginOk):
        log.info("re-login for %s failed: %s", tg_id, type(result).__name__)
        await _drop(tg_id)
        raise NeedsLogin()
    await db.save_cookies(tg_id, crypto.encrypt(json.dumps(s.client.export_cookies())))


async def fetch(tg_id: int, url: str, cache: bool = True) -> str:
    s = await _session(tg_id)
    async with s.lock:
        hit = s.cache.get(url) if cache else None
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        try:
            r = await s.client.get(url)
        except SessionExpired:
            await _relogin(tg_id, s)
            r = await s.client.get(url)
        if cache:
            s.cache[url] = (time.monotonic(), r.text)
        return r.text


async def teacher(tg_id: int) -> parsers.TeacherInfo:
    s = await _session(tg_id)
    if s.teacher:
        return s.teacher
    try:
        html = await fetch(tg_id, f"{BASE}/myclasses")
        school_id = parsers.parse_school_id(html)
        tab = await fetch(tg_id, f"{BASE}/schedules/?school={school_id}&tab=teachers") if school_id else ""
    except httpx.HTTPStatusError as e:
        log.info("teacher pages refused for %s: %s", tg_id, e.response.status_code)
        raise NotTeacher() from e
    teacher_id, full_name = parsers.parse_teacher_select(tab)
    if not teacher_id:
        raise NotTeacher()
    classes = parsers.parse_my_classes(html)
    s.teacher = parsers.TeacherInfo(full_name, teacher_id, school_id, parsers.parse_school_name(tab), classes)
    return s.teacher


def _day_q(d: date) -> str:
    return f"year={d.year}&month={d.month}&day={d.day}"


async def teacher_week(tg_id: int, d: date) -> list[parsers.Lesson]:
    t = await teacher(tg_id)
    html = await fetch(tg_id, f"{BASE}/schedules/?school={t.school_id}&tab=teachers&teacher={t.teacher_id}&{_day_q(d)}")
    return parsers.parse_teacher_week(html)


async def class_week(tg_id: int, group_id: str, d: date) -> list[parsers.Lesson]:
    t = await teacher(tg_id)
    html = await fetch(tg_id, f"{BASE}/schedules/view?school={t.school_id}&group={group_id}&{_day_q(d)}")
    return parsers.parse_class_week(html)


async def class_homework(tg_id: int, group_id: str) -> tuple[int, list[parsers.Homework]]:
    t = await teacher(tg_id)
    html = await fetch(tg_id, f"{BASE}/homework?view=List&school={t.school_id}&group={group_id}")
    return parsers.parse_homework(html)


# ---- BSB / ChSB ("Sinf bo'yicha BSB/CHSB detalizatsiyasi" report) ----
# The page builds the report through GET-only handlers: start a task, poll its state, fetch the HTML.
REPORT_HANDLER = f"{BASE}/AsyncProgressReportHandler"
TASK_STATE = f"{BASE}/TaskStateHandler"
TASK_DONE, TASK_FAILED = 3, 4


def _study_year() -> int:
    """emaktab names a school year by its first calendar year (2026/2027 → 2026)."""
    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    return today.year if today.month >= 8 else today.year - 1


async def summative_subjects(tg_id: int, group_id: str) -> list[tuple[str, str]]:
    t = await teacher(tg_id)
    html = await fetch(tg_id, f"{BASE}/reports/default?school={t.school_id}&report=sorch-monitoring-group"
                              f"&year={_study_year()}&group={group_id}")
    return parsers.parse_report_subjects(html)


async def summative(tg_id: int, group_id: str, subject_id: str, quarter: int) -> parsers.SummativeReport:
    """BSB/ChSB results of one class and subject for quarter 1..4."""
    t = await teacher(tg_id)
    s = await _session(tg_id)
    key = f"summative:{group_id}:{subject_id}:{quarter}"
    hit = s.cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    q = (f"sid={t.school_id}&sy={_study_year()}&pn={quarter - 1}&rpt=5&gid={group_id}"
         f"&sbid={subject_id}&tcid={t.teacher_id}")
    task = json.loads(await fetch(tg_id, f"{REPORT_HANDLER}?a=buildSorchMonitoringGroupReportData&{q}", cache=False))
    tid = task["taskID"]
    for _ in range(25):
        state = json.loads(await fetch(tg_id, f"{TASK_STATE}?a=gts&tid={tid}", cache=False))
        if state.get("taskStatus") in (TASK_DONE, TASK_FAILED):
            break
        await asyncio.sleep(1.5)
    else:
        raise TimeoutError("BSB/ChSB report was not ready in time")
    if state["taskStatus"] == TASK_FAILED:
        report = parsers.SummativeReport()
    else:
        data = json.loads(await fetch(tg_id, f"{REPORT_HANDLER}?a=htmlSorchMonitoringGroupReportData&tid={tid}&{q}",
                                      cache=False))
        report = parsers.parse_summative(data.get("result") or "")
    s.cache[key] = (time.monotonic(), report)
    return report


# ---- Homework statuses (maqom) ----
def _work_url(school_id: str, work_id: str) -> str:
    return f"{BASE}/homework?school={school_id}&work={work_id}"


async def homework_detail(tg_id: int, work_id: str, fresh: bool = False) -> parsers.HomeworkDetail:
    t = await teacher(tg_id)
    return parsers.parse_homework_detail(await fetch(tg_id, _work_url(t.school_id, work_id), cache=not fresh), work_id)


class StatusChangeError(Exception):
    pass


async def change_status(tg_id: int, work_id: str, person_id: str, action: str) -> tuple[str, str]:
    """Change one student's status; returns (old label, new label). Always re-reads the page first,
    so the action is checked against the student's current status and the page's fresh token."""
    t = await teacher(tg_id)
    detail = await homework_detail(tg_id, work_id, fresh=True)
    st = next((x for x in detail.students if x.person_id == person_id), None)
    if st is None:
        raise StatusChangeError("O‘quvchi bu vazifada topilmadi")
    if action not in parsers.STATUS_ACTIONS.get(st.code, []):
        raise StatusChangeError(f"“{st.label}” maqomida bu amal mumkin emas")
    if not detail.change_url:
        raise StatusChangeError("Sahifada maqom o‘zgartirish imkoni topilmadi")
    s = await _session(tg_id)
    error, new_label = "", ""
    try:
        async with s.lock:
            try:
                res = await s.client.change_status(detail.change_url, work_id, person_id, action)
            except SessionExpired:
                await _relogin(tg_id, s)
                fresh = await homework_detail(tg_id, work_id, fresh=True)
                res = await s.client.change_status(fresh.change_url, work_id, person_id, action)
        error = str(res.get("error") or "")
        new_label = str(res.get("v") or "")
    except (httpx.HTTPError, ValueError) as e:
        error = f"{type(e).__name__}: {e}"
    log.info("status change by %s: work %s person %s %s -> %s %s", tg_id, work_id, person_id, action,
             new_label, error or "ok")
    await db.log_status_change(tg_id, work_id, person_id, st.name, action, st.label, new_label, error)
    # The page and the class list changed on emaktab: drop their cached copies
    for key in [k for k in s.cache if f"work={work_id}" in k or "/homework?view=List" in k]:
        s.cache.pop(key, None)
    if error:
        raise StatusChangeError(error)
    return st.label, new_label
