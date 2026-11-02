"""SQLite access. Each function opens its own connection — the load is small."""
from datetime import datetime

import aiosqlite

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY,
    telegram_id  INTEGER NOT NULL UNIQUE,
    username     TEXT,
    full_name    TEXT,
    created_at   TEXT NOT NULL
);

-- emaktab credentials; password and cookies are Fernet-encrypted (see crypto.py)
CREATE TABLE IF NOT EXISTS accounts (
    telegram_id      INTEGER PRIMARY KEY,
    login            TEXT NOT NULL,
    password_enc     TEXT NOT NULL,
    cookies_enc      TEXT,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_failures (
    telegram_id      INTEGER PRIMARY KEY,
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     TEXT
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()


async def upsert_user(telegram_id: int, username: str | None, full_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO users (telegram_id, username, full_name, created_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET username = excluded.username, full_name = excluded.full_name""",
            (telegram_id, username, full_name, datetime.now().isoformat(timespec="seconds")),
        )
        await conn.commit()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


async def get_account(telegram_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM accounts WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
    return dict(row) if row else None


async def save_account(telegram_id: int, login: str, password_enc: str, cookies_enc: str) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO accounts (telegram_id, login, password_enc, cookies_enc, updated_at) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET login = excluded.login, password_enc = excluded.password_enc,
                   cookies_enc = excluded.cookies_enc, updated_at = excluded.updated_at""",
            (telegram_id, login, password_enc, cookies_enc, _now()),
        )
        await conn.commit()


async def save_cookies(telegram_id: int, cookies_enc: str) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE accounts SET cookies_enc = ?, updated_at = ? WHERE telegram_id = ?",
            (cookies_enc, _now(), telegram_id),
        )
        await conn.commit()


async def delete_account(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM accounts WHERE telegram_id = ?", (telegram_id,))
        await conn.commit()


# Failed-login bookkeeping lives in its own table so it works before an account exists
async def get_lock(telegram_id: int) -> tuple[int, str | None]:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT failed_attempts, locked_until FROM login_failures WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cur.fetchone()
    return (row[0], row[1]) if row else (0, None)


async def set_lock(telegram_id: int, failed_attempts: int, locked_until: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """INSERT INTO login_failures (telegram_id, failed_attempts, locked_until) VALUES (?, ?, ?)
               ON CONFLICT(telegram_id) DO UPDATE SET failed_attempts = excluded.failed_attempts,
                   locked_until = excluded.locked_until""",
            (telegram_id, failed_attempts, locked_until),
        )
        await conn.commit()
