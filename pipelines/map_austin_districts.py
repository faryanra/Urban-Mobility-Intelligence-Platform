"""Attach council districts to loaded Austin trips and place trip ends at district centroids.

The public dataset reports where trips start and end by council district, not by coordinate.
"""

import asyncio

import asyncpg
import httpx

from pipelines.db import DATABASE_URL

SOCRATA = "https://data.austintexas.gov/resource/7d8e-dm7r.json"

# Filter to the same date range our DB trips came from
DATE_FILTER = (
    "start_time >= '2021-10-10T00:00:00' "
    "AND start_time <= '2021-10-14T00:00:00' "
    "AND council_district_start IS NOT NULL "
    "AND council_district_end IS NOT NULL"
)


async def fetch_socrata(client: httpx.AsyncClient) -> list[dict]:
    records = []
    offset = 0
    while True:
        params = {
            "$limit": 5000,
            "$offset": offset,
            "$select": "trip_id,council_district_start,council_district_end",
            "$where": DATE_FILTER,
        }
        resp = await client.get(SOCRATA, params=params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        records.extend(rows)
        offset += len(rows)
        print(f"  fetched {len(records)} rows...")
        if len(rows) < 5000:
            break
    return records


async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        print("Fetching Socrata records (Oct 10–13 2021)...")
        records = await fetch_socrata(client)
    print(f"Total Socrata rows: {len(records)}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        centroid_rows = await conn.fetch("""
            SELECT district_id,
                   ST_Y(centroid::geometry) AS lat,
                   ST_X(centroid::geometry) AS lng
            FROM austin_districts
        """)
        centroids = {
            str(r["district_id"]): (float(r["lat"]), float(r["lng"]))
            for r in centroid_rows
        }
        print(f"Loaded {len(centroids)} centroids: {sorted(centroids.keys())}")

        await conn.execute("""
            CREATE TEMP TABLE austin_district_map (
                trip_id TEXT,
                district_start TEXT,
                district_end TEXT
            )
        """)

        batch = []
        for row in records:
            trip_id = row.get("trip_id", "")
            d_start = str(row.get("council_district_start", "")).strip()
            d_end   = str(row.get("council_district_end",   "")).strip()
            if trip_id and d_start in centroids and d_end in centroids:
                batch.append((trip_id, d_start, d_end))

        await conn.copy_records_to_table(
            "austin_district_map",
            records=batch,
            columns=["trip_id", "district_start", "district_end"],
        )
        print(f"Inserted {len(batch)} rows into temp table")

        result = await conn.execute("""
            UPDATE mobility_trips mt
            SET
                council_district_start = m.district_start,
                council_district_end   = m.district_end,
                origin_lat  = d_s.lat,
                origin_lng  = d_s.lng,
                dest_lat    = d_e.lat,
                dest_lng    = d_e.lng,
                origin_geom = ST_SetSRID(ST_MakePoint(d_s.lng, d_s.lat), 4326),
                dest_geom   = ST_SetSRID(ST_MakePoint(d_e.lng, d_e.lat), 4326)
            FROM austin_district_map m
            JOIN (
                SELECT district_id,
                       ST_Y(centroid::geometry) AS lat,
                       ST_X(centroid::geometry) AS lng
                FROM austin_districts
            ) d_s ON d_s.district_id::text = m.district_start
            JOIN (
                SELECT district_id,
                       ST_Y(centroid::geometry) AS lat,
                       ST_X(centroid::geometry) AS lng
                FROM austin_districts
            ) d_e ON d_e.district_id::text = m.district_end
            WHERE mt.trip_id = m.trip_id AND mt.city = 'austin'
        """)
        print(f"UPDATE result: {result}")

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM mobility_trips WHERE city = 'austin' AND origin_geom IS NOT NULL"
        )
        print(f"Austin trips with origin_geom: {count}")

    finally:
        await conn.close()


asyncio.run(main())
