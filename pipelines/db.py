"""Database connection string shared by all pipeline scripts."""

import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mobility_user:mobility_pass@127.0.0.1:5434/mobility_db",
)
