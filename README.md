<p align="center"><img src="assets/logo.png" width="140" alt="Jurnalim"></p>

# Jurnalim

[@jurnalimbot](https://t.me/jurnalimbot) — Telegram bot for teachers: their eMaktab.uz schedule, classes
and homework right in Telegram. Python 3.12, aiogram 3, SQLite.

> Independent project, not an official eMaktab app.

## Features
- 🗓 **Bugungi darslarim** — today's lessons with finished ✅ / current 🔴 / next lesson
- 📅 **Haftalik jadvalim** — weekly schedule with week navigation
- 📚 **Sinflarim** — every class: its weekly schedule and homework list
- ✏️ **Maqom berish** — class → homework → student → new status (Tekshirish va yopish / Qayta ko‘rib chiqishga / Bekor qilish), with confirmation
- 📊 **BSB / ChSB** — per class, subject and quarter: each student's BSB/ChSB points and quarter grade, class averages and grade counts (from eMaktab's "Sinf bo'yicha BSB/CHSB detalizatsiyasi" report, built through its GET-only handlers)
- 👤 **Profil** — name, school, classes
- 🔑 Login with eMaktab credentials; if the site asks for a captcha, the user solves it in the chat

## Read-only, with one exception
The bot changes nothing on eMaktab except, at the account owner's request, a student's homework status
(✏️ **Maqom berish**). `src/emaktab/client.py` sends two kinds of POST: the login form and that status change
(only the page's own actions, after an explicit confirmation, logged to `status_changes`). Everything else is a
GET; grades are never changed, and logout/localization links are refused.

## Security
- Passwords and session cookies are stored Fernet-encrypted (`ENCRYPTION_KEY` in `.env` — never change or lose it).
- The password message is deleted from the chat right after it is read.
- After 2 wrong passwords the user is locked for 10 minutes, so eMaktab's captcha is rarely triggered.
- `/chiqish` removes the user's login, password and session from the bot.
- `OPEN_TO_ALL=1` opens the bot to everyone; with `0` only `ADMIN_IDS` can use it and others get a "test mode" reply.
- The menus are for teacher accounts; student/parent accounts get a clear "teachers only for now" message.

## Layout
```
run.py                    entry point (polling, admin filter)
src/config.py             settings from .env
src/crypto.py             Fernet helpers
src/db.py                 SQLite: users, accounts, login_failures
src/session.py            per-user sessions: login, re-login, page cache
src/emaktab/client.py     read-only HTTP client, captcha handling
src/emaktab/parsers.py    HTML → data (classes, schedules, homework)
src/formatting.py         data → Telegram HTML messages
src/keyboards.py          reply / inline keyboards
src/handlers/             start, auth (login FSM), menu, guest
deploy/jurnalim.service   systemd unit
```

## Run

```bash
cd /home/jurnalim
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # BOT_TOKEN, ADMIN_IDS, ENCRYPTION_KEY
.venv/bin/python run.py
```

Generate an encryption key once:
```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Server (systemd)

```bash
sudo cp deploy/jurnalim.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jurnalim
journalctl -u jurnalim -f
```
