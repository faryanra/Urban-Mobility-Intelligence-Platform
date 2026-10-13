"""Load Austin council district GeoJSON into PostGIS."""
import asyncio
import json
from pathlib import Path

import asyncpg
from shapely.geometry import MultiPolygon, Polygon, shape

GEOJSON = Path("pipelines/data/raw/austin_council_districts.geojson")


def to_multipolygon(geom):
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError(f"Unsupported geometry type: {type(geom)}")


async def main():
    conn = await asyncpg.connect(
        host='127.0.0.1', port=5434, database='mobility_db',
        user='mobility_user', password='mobility_pass',
    )
    data = json.loads(GEOJSON.read_text())

    await conn.execute("TRUNCATE austin_districts RESTART IDENTITY CASCADE")

    loaded = 0
    for feature in data["features"]:
        props = feature.get("properties", {})
        district_id = str(
            props.get("COUNCIL_DISTRICT") or
            props.get("council_district") or
            props.get("district_id") or
            props.get("DISTRICT") or
            props.get("district") or
            props.get("OBJECTID") or
            props.get("objectid") or
            loaded + 1
        )
        district_name = f"District {district_id}"

        geom = to_multipolygon(shape(feature["geometry"]))
        centroid = geom.centroid

        await conn.execute("""
            INSERT INTO austin_districts (district_id, district_name, geom, centroid)
            VALUES ($1, $2, ST_GeomFromText($3, 4326), ST_GeomFromText($4, 4326))
            ON CONFLICT (district_id) DO NOTHING
        """, district_id, district_name, geom.wkt, centroid.wkt)
        loaded += 1

    await conn.close()
    print(f"Loaded {loaded} Austin council districts")

asyncio.run(main())
