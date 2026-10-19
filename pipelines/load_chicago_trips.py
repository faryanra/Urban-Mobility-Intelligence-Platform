"""Load the Chicago Divvy 2013 trip sample into PostGIS."""
import asyncio
from pathlib import Path

import asyncpg
import pandas as pd

from pipelines.db import DATABASE_URL

CSV = Path("pipelines/data/raw/chicago_divvy_trips_june2013.csv")
COLUMNS = {
    "trip_id": "trip_id",
    "from_station_id": "from_station_id",
    "from_station_name": "from_station_name",
    "to_station_id": "to_station_id",
    "to_station_name": "to_station_name",
    "from_latitude": "from_lat",
    "from_longitude": "from_lng",
    "to_latitude": "to_lat",
    "to_longitude": "to_lng",
    "trip_duration": "duration_sec",
    "start_time": "start_time",
    "user_type": "user_type",
}


def read_trips() -> pd.DataFrame:
    df = pd.read_csv(CSV, usecols=list(COLUMNS)).rename(columns=COLUMNS)
    df = df.dropna(subset=["from_station_id", "to_station_id", "from_lat", "from_lng", "to_lat", "to_lng"])
    for col in ("trip_id", "from_station_id", "to_station_id"):
        df[col] = df[col].astype("int64").astype(str)
    df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce")
    df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce")
    return df


def to_record(r) -> tuple:
    return (
        r.trip_id, r.from_station_id, r.from_station_name, r.to_station_id, r.to_station_name,
        float(r.from_lat), float(r.from_lng), float(r.to_lat), float(r.to_lng),
        None if pd.isna(r.duration_sec) else int(r.duration_sec),
        None if pd.isna(r.start_time) else r.start_time.to_pydatetime(),
        None if pd.isna(r.user_type) else r.user_type,
    )


async def main():
    records = [to_record(r) for r in read_trips().itertuples(index=False)]

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("TRUNCATE chicago_trips RESTART IDENTITY")
        await conn.copy_records_to_table(
            "chicago_trips", records=records, columns=list(COLUMNS.values())
        )
        count = await conn.fetchval("SELECT COUNT(*) FROM chicago_trips")
    finally:
        await conn.close()
    print(f"Loaded {count:,} Chicago trips")


asyncio.run(main())
