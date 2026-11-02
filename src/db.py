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
