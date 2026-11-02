# Jurnalim

Telegram bot (Python 3.12, aiogram 3, SQLite).

## Ishga tushirish

```bash
cd /home/jurnalim
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # BOT_TOKEN ni kiriting
.venv/bin/python run.py
```

## Server (systemd)

```bash
sudo cp deploy/jurnalim.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jurnalim
journalctl -u jurnalim -f
```
