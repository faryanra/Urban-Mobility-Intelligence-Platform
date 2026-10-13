"""Load Chicago Divvy June 2013 trips with station lat/lon lookup."""
import asyncio
from pathlib import Path

import asyncpg
import pandas as pd


async def main():
    conn = await asyncpg.connect(
        host='127.0.0.1', port=5434, database='mobility_db',
        user='mobility_user', password='mobility_pass',
    )

    df = pd.read_csv(Path("pipelines/data/raw/chicago_divvy_trips_june2013.csv"))
    print(f"Loaded CSV: {len(df)} rows")
    print(f"Columns: {df.columns.tolist()}")

    cols_lower = {c.lower().strip(): c for c in df.columns}

    from_station_col = (cols_lower.get("from_station_id") or cols_lower.get("start_station_id") or
                        cols_lower.get("from station id") or cols_lower.get("bikeid"))
    to_station_col   = (cols_lower.get("to_station_id")   or cols_lower.get("end_station_id")   or
                        cols_lower.get("to station id"))
    from_lat_col     = (cols_lower.get("from_latitude")   or cols_lower.get("start_lat") or
                        cols_lower.get("latitude") or cols_lower.get("from latitude"))
    from_lng_col     = (cols_lower.get("from_longitude")  or cols_lower.get("start_lng") or
                        cols_lower.get("longitude") or cols_lower.get("from longitude"))
    to_lat_col       = (cols_lower.get("to_latitude")     or cols_lower.get("end_lat") or
                        cols_lower.get("to latitude"))
    to_lng_col       = (cols_lower.get("to_longitude")    or cols_lower.get("end_lng") or
                        cols_lower.get("to longitude"))
    duration_col     = (cols_lower.get("tripduration")    or cols_lower.get("trip_duration") or
                        cols_lower.get("duration"))
    start_time_col   = (cols_lower.get("starttime")       or cols_lower.get("start_time") or
                        cols_lower.get("started_at"))
    trip_id_col      = cols_lower.get("trip_id") or cols_lower.get("id")
    user_type_col    = (cols_lower.get("usertype")        or cols_lower.get("user_type") or
                        cols_lower.get("member_casual"))

    print(f"Mapped from_station: {from_station_col}, to_station: {to_station_col}")
    print(f"Mapped from_lat: {from_lat_col}, from_lng: {from_lng_col}")
    print(f"Mapped to_lat: {to_lat_col}, to_lng: {to_lng_col}")

    has_latlon = bool(from_lat_col and to_lat_col)

    if not has_latlon:
        print("No lat/lon in trip data — looking up from stations table")
        station_rows = await conn.fetch(
            "SELECT station_id, lat, lng FROM stations WHERE city = 'chicago'"
        )
        station_map = {str(r["station_id"]): (r["lat"], r["lng"]) for r in station_rows}
        print(f"Station lookup map: {len(station_map)} stations")
    else:
        station_map = {}

    await conn.execute("TRUNCATE chicago_trips RESTART IDENTITY CASCADE")

    batch = []
    skipped = 0
    for _, row in df.iterrows():
        try:
            from_id = str(row[from_station_col]) if from_station_col else None
            to_id   = str(row[to_station_col])   if to_station_col   else None

            if has_latlon:
                from_lat = float(row[from_lat_col]) if from_lat_col and pd.notna(row.get(from_lat_col)) else None
                from_lng = float(row[from_lng_col]) if from_lng_col and pd.notna(row.get(from_lng_col)) else None
                to_lat   = float(row[to_lat_col])   if to_lat_col   and pd.notna(row.get(to_lat_col))   else None
                to_lng   = float(row[to_lng_col])   if to_lng_col   and pd.notna(row.get(to_lng_col))   else None
            else:
                coords_from = station_map.get(from_id, (None, None))
                coords_to   = station_map.get(to_id,   (None, None))
                from_lat, from_lng = coords_from
                to_lat,   to_lng   = coords_to

            if from_lat is None or to_lat is None:
                skipped += 1
                continue

            duration  = int(float(row[duration_col]))  if duration_col  and pd.notna(row.get(duration_col))  else None
            start_ts  = pd.to_datetime(row[start_time_col]).to_pydatetime() if start_time_col and pd.notna(row.get(start_time_col)) else None
            trip_id   = str(row[trip_id_col])   if trip_id_col   else None
            user_type = str(row[user_type_col]) if user_type_col else None

            batch.append((trip_id, from_id, to_id, from_lat, from_lng,
                          to_lat, to_lng, duration, start_ts, user_type))
        except (ValueError, TypeError, KeyError):
            skipped += 1

    await conn.executemany("""
        INSERT INTO chicago_trips
            (trip_id, from_station_id, to_station_id,
             from_lat, from_lng, to_lat, to_lng,
             duration_sec, start_time, user_type)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
    """, batch)

    count = await conn.fetchval("SELECT COUNT(*) FROM chicago_trips")
    await conn.close()
    print(f"Loaded {count} trips, skipped {skipped}")

asyncio.run(main())
