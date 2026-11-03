import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
# 1: everyone can use the bot; 0: only ADMIN_IDS (everyone else gets the "test mode" reply)
OPEN_TO_ALL = os.getenv("OPEN_TO_ALL", "0") == "1"
DB_PATH = str(BASE_DIR / os.getenv("DB_PATH", "data/bot.db"))
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
TIMEZONE = "Asia/Tashkent"

# Wrong-password protection: emaktab shows a captcha after ~3 failures, so stop earlier
MAX_FAILED_LOGINS = 2
LOGIN_LOCK_MINUTES = 10
# Pages are cached per user this long to keep request volume to emaktab low
CACHE_SECONDS = 300


def is_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS
