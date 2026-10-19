"""Database and app configuration, read from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mobility_user:mobility_pass@127.0.0.1:5434/mobility_db",
)

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3002"
    ).split(",")
    if o.strip()
]

OSM_CACHE_DIR = Path(
    os.getenv("OSM_CACHE_DIR", Path(__file__).parent / "data" / "osm_cache")
)
