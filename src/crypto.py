"""Fernet encryption for emaktab passwords and session cookies stored in SQLite."""
from cryptography.fernet import Fernet

from .config import ENCRYPTION_KEY

_fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


def encrypt(text: str) -> str:
    return _fernet.encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
