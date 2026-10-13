"""Download Chicago station locations and load into PostGIS."""


import psycopg2
import requests

DSN = "host=127.0.0.1 port=5434 dbname=mobility_db user=mobility_user password=mobility_pass"

# Divvy stations 2013 — public JSON from Chicago Open Data
STATIONS_URL = "https://data.cityofchicago.org/resource/bbyy-e7gq.json?$limit=1000"


def load_stations() -> None:
    print("Fetching Chicago station locations...")
    r = requests.get(STATIONS_URL, timeout=30)
    r.raise_for_status()
    stations = r.json()
    print(f"  fetched {len(stations)} stations")

    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    inserted = 0

    for s in stations:
        try:
            lat = float(s.get("latitude") or s.get("lat") or 0)
            lon = float(s.get("longitude") or s.get("lon") or 0)
            if not lat or not lon:
                continue
            cur.execute("""
                INSERT INTO stations (station_id, name, city, geom)
                VALUES (%s, %s, 'chicago', ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ON CONFLICT (station_id, city) DO NOTHING
            """, (
                str(s.get("id") or s.get("station_id", "")),
                s.get("station_name") or s.get("name", ""),
                lon, lat,
            ))
            inserted += 1
        except (ValueError, TypeError, KeyError):
            continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"  inserted {inserted} stations")


if __name__ == "__main__":
    load_stations()
