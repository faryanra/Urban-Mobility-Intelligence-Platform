"""Database and app configuration."""

import os
import urllib.parse

from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL")

if _db_url:
    _p = urllib.parse.urlparse(_db_url)
    DB_HOST = _p.hostname or "127.0.0.1"
    DB_PORT = _p.port or 5432
    DB_NAME = (_p.path or "").lstrip("/")
    DB_USER = _p.username or "mobility_user"
    DB_PASS = _p.password or ""
    DATABASE_URL = _db_url
else:
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "5434"))
    DB_NAME = os.getenv("DB_NAME", "mobility_db")
    DB_USER = os.getenv("DB_USER", "mobility_user")
    DB_PASS = os.getenv("DB_PASS", "mobility_pass")
    DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
