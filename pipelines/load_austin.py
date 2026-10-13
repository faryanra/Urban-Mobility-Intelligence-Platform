"""Load cleaned Austin trips into PostGIS."""

from pathlib import Path

import pandas as pd
import psycopg2

PARQUET = Path("pipelines/data/processed/austin_clean.parquet")
DSN = "host=127.0.0.1 port=5434 dbname=mobility_db user=mobility_user password=mobility_pass"


def load() -> None:
    df = pd.read_parquet(PARQUET)
    print(f"Loading {len(df):,} Austin trips...")

    # Austin Socrata API columns — find lat/lon
    lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
    lon_col = next((c for c in df.columns if "lon" in c.lower()), None)
    print(f"  coordinate columns: lat={lat_col}, lon={lon_col}")

    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        try:
            origin_geom = None
            if lat_col and lon_col:
                lat = row.get(lat_col)
                lon = row.get(lon_col)
                if pd.notna(lat) and pd.notna(lon):
                    origin_geom = f"SRID=4326;POINT({float(lon)} {float(lat)})"

            cur.execute("""
                INSERT INTO mobility_trips
                  (trip_id, start_time, end_time, duration_sec, vehicle_type, origin_geom, city)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                str(row.get("trip_id", ""))[:100],
                row.get("start_time"),
                row.get("end_time"),
                int(row["trip_duration"]) if pd.notna(row.get("trip_duration")) else None,
                str(row.get("vehicle_type", "unknown"))[:20],
                origin_geom,
                "austin",
            ))
            inserted += 1
        except (ValueError, TypeError, KeyError):
            skipped += 1
            continue

        if inserted % 5000 == 0:
            conn.commit()
            print(f"  {inserted:,} inserted...")

    conn.commit()
    cur.close()
    conn.close()
    print(f"Done: {inserted:,} inserted, {skipped:,} skipped")


if __name__ == "__main__":
    load()
