"""Load Chicago wards and CTA L lines into PostGIS."""
import asyncio
import json
from pathlib import Path

import asyncpg
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape


def to_multipolygon(geom):
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError(f"Unsupported geometry type: {type(geom)}")


def to_multilinestring(geom):
    if isinstance(geom, MultiLineString):
        return geom
    if isinstance(geom, LineString):
        return MultiLineString([geom])
    raise ValueError(f"Unsupported geometry type: {type(geom)}")


async def load_wards(conn):
    data = json.loads(Path("pipelines/data/raw/chicago_wards.geojson").read_text())
    await conn.execute("TRUNCATE chicago_wards RESTART IDENTITY CASCADE")
    loaded = 0
    for i, feature in enumerate(data["features"]):
        props = feature.get("properties", {})
        ward_id = str(
            props.get("ward") or props.get("WARD") or
            props.get("ward_id") or i + 1
        )
        geom = to_multipolygon(shape(feature["geometry"]))
        centroid = geom.centroid
        await conn.execute("""
            INSERT INTO chicago_wards (ward_id, geom, centroid)
            VALUES ($1, ST_GeomFromText($2, 4326), ST_GeomFromText($3, 4326))
            ON CONFLICT (ward_id) DO NOTHING
        """, ward_id, geom.wkt, centroid.wkt)
        loaded += 1
    print(f"Loaded {loaded} Chicago wards")


async def load_metro(conn):
    data = json.loads(Path("pipelines/data/raw/chicago_cta_lines.geojson").read_text())
    await conn.execute("TRUNCATE chicago_metro_lines RESTART IDENTITY CASCADE")
    loaded = 0
    for feature in data["features"]:
        props = feature.get("properties", {})
        line_name = props.get("lines") or props.get("name") or props.get("LINES") or "L"
        color = props.get("legend") or props.get("color") or None
        geom = to_multilinestring(shape(feature["geometry"]))
        await conn.execute("""
            INSERT INTO chicago_metro_lines (line_name, color, geom)
            VALUES ($1, $2, ST_GeomFromText($3, 4326))
        """, line_name, color, geom.wkt)
        loaded += 1
    print(f"Loaded {loaded} CTA L lines")


async def main():
    conn = await asyncpg.connect(
        host='127.0.0.1', port=5434, database='mobility_db',
        user='mobility_user', password='mobility_pass',
    )
    await load_wards(conn)
    await load_metro(conn)
    await conn.close()

asyncio.run(main())
