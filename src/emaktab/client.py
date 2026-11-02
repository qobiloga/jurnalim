"""Read-only HTTP client for emaktab.uz.

The only POST this client ever sends is the login form. Everything else is a GET
to an emaktab.uz page, so the bot can never change anything on the platform.
"""
import json
import re
import uuid
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

LOGIN_URL = "https://login.emaktab.uz/"
DEFAULT_CAPTCHA_PART = "https://login.emaktab.uz/captcha/true/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
# GET links that still change state on the server — never follow them
FORBIDDEN_PATHS = ("logout", "/api/localization/change")


class SessionExpired(Exception):
    """emaktab redirected to the login page: the cookies are no longer valid."""


@dataclass
class LoginOk:
    pass


@dataclass
class WrongCredentials:
    message: str


@dataclass
class CaptchaRequired:
    captcha_id: str
    image: bytes
    wrong_answer: bool = False


LoginResult = LoginOk | WrongCredentials | CaptchaRequired


def _decode_js(s: str) -> str:
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)


def _login_state(html: str) -> dict:
    """The login page embeds its form state as JSON inside a require() call."""
    m = re.search(r"JSON\.parse\('([^']*hasErrors[^']*)'\)", html)
    if not m:
        return {}
    try:
        return json.loads(_decode_js(m.group(1)))
    except ValueError:
        return {}


def _captcha_part(html: str) -> str:
    m = re.search(r'"imagePart"\s*:\s*"([^"]+)"', _decode_js(html))
    return m.group(1) if m else DEFAULT_CAPTCHA_PART


def _exceeded(html: str) -> bool:
    m = re.search(r'name="exceededAttempts"[^>]*value="(\w+)"', html) or re.search(
        r'value="(\w+)"[^>]*name="exceededAttempts"', html
    )
    return bool(m) and m.group(1).lower() == "true"


class EmaktabClient:
    def __init__(self, cookies: list[dict] | None = None) -> None:
        self._http = httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=30)
        for c in cookies or []:
            self._http.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))

    async def close(self) -> None:
        await self._http.aclose()

    def export_cookies(self) -> list[dict]:
        return [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in self._http.cookies.jar
        ]

    async def new_captcha(self, part: str = DEFAULT_CAPTCHA_PART, wrong_answer: bool = False) -> CaptchaRequired:
        captcha_id = str(uuid.uuid4())
        r = await self._http.get(part + captcha_id)
        return CaptchaRequired(captcha_id, r.content, wrong_answer)

    async def login(
        self, login: str, password: str, captcha_id: str | None = None, captcha_answer: str | None = None
    ) -> LoginResult:
        page = await self._http.get(LOGIN_URL)
        if urlparse(str(page.url)).hostname != "login.emaktab.uz":
            return LoginOk()  # cookies are still valid
        part = _captcha_part(page.text)
        # Don't spend an attempt we know will be refused without a captcha
        if _exceeded(page.text) and not captcha_answer:
            return await self.new_captcha(part)

        data = {
            "exceededAttempts": "True" if captcha_answer else "False",
            "ReturnUrl": "",
            "FingerprintId": "",
            "login": login,
            "password": password,
        }
        if captcha_answer:
            data["Captcha.Id"] = captcha_id or ""
            data["Captcha.Input"] = captcha_answer
        r = await self._http.post(LOGIN_URL, data=data)
        if urlparse(str(r.url)).hostname != "login.emaktab.uz":
            return LoginOk()

        state = _login_state(r.text)
        if state.get("isWrongCaptcha"):
            return await self.new_captcha(_captcha_part(r.text), wrong_answer=True)
        if state.get("exceededAttempts") or _exceeded(r.text):
            return await self.new_captcha(_captcha_part(r.text))
        return WrongCredentials(state.get("firstErrorText") or "Login yoki parol noto‘g‘ri")

    async def get(self, url: str) -> httpx.Response:
        host = urlparse(url).hostname or ""
        if not (host == "emaktab.uz" or host.endswith(".emaktab.uz")):
            raise ValueError(f"Not an emaktab URL: {url}")
        if any(p in url for p in FORBIDDEN_PATHS):
            raise ValueError(f"Refusing state-changing URL: {url}")
        r = await self._http.get(url)
        if urlparse(str(r.url)).hostname == "login.emaktab.uz":
            raise SessionExpired()
        r.raise_for_status()
        return r
