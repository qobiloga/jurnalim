import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
DB_PATH = str(BASE_DIR / os.getenv("DB_PATH", "data/bot.db"))


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS
