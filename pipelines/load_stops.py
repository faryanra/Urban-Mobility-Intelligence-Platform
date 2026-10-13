"""Load parsed GTFS stops from parquet into PostGIS transit_stops table."""

from pathlib import Path

import geopandas as gpd
import psycopg2

DSN = "host=127.0.0.1 port=5434 dbname=mobility_db user=mobility_user password=mobility_pass"

FILES = {
    "stockholm": Path("pipelines/data/processed/stockholm_stops.parquet"),
    "amsterdam": Path("pipelines/data/processed/amsterdam_stops.parquet"),
}


def load_stops() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    for city, path in FILES.items():
        if not path.exists():
            print(f"  skip {city}: parquet not found")
            continue
        gdf = gpd.read_parquet(path)
        print(f"  {city}: {len(gdf):,} stops")
        inserted = 0
        for _, row in gdf.iterrows():
            geom_wkt = f"SRID=4326;POINT({row.geometry.x} {row.geometry.y})"
            cur.execute("""
                INSERT INTO transit_stops (stop_id, stop_name, city, geom)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (stop_id, city) DO NOTHING
            """, (str(row["stop_id"]), str(row.get("stop_name", "")), city, geom_wkt))
            inserted += 1
        conn.commit()
        print(f"    inserted {inserted:,}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    load_stops()
