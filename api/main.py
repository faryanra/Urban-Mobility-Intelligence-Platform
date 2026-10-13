"""Urban Mobility Intelligence Platform — REST API."""

import json
from contextlib import asynccontextmanager
from pathlib import Path

import networkx as nx
import osmnx as ox
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from api.config import CORS_ORIGINS
from api.database import close_pool, get_pool

_ROOT = Path(__file__).parent.parent
PROCESSED = _ROOT / "spatial" / "data" / "processed"
STOPS_DIR = _ROOT / "pipelines" / "data" / "processed"
OSM_CACHE_DIR = Path(__file__).parent / "data" / "osm_cache"

OSM_CITIES = {
    "stockholm": "stockholm_walk.graphml",
    "amsterdam": "amsterdam_walk.graphml",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    app.state.osm_graphs = {}
    for city, fname in OSM_CITIES.items():
        path = OSM_CACHE_DIR / fname
        if path.exists():
            G = ox.load_graphml(str(path))
            app.state.osm_graphs[city] = G
            print(f"Loaded OSM graph: {city} ({len(G.nodes)} nodes)")
        else:
            print(f"WARNING: OSM graph not found: {path}")
    yield
    await close_pool()


app = FastAPI(title="Urban Mobility Intelligence Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT version()")
    return {"status": "ok", "db": row["version"][:30]}


@app.get("/api/trips/summary")
async def trips_summary():
    """Trip count and avg duration per city."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT city,
                   COUNT(*)            AS trip_count,
                   AVG(duration_sec)   AS avg_duration_sec
            FROM mobility_trips
            GROUP BY city
            ORDER BY city
        """)
    return [dict(r) for r in rows]


@app.get("/api/stations")
async def stations(city: str | None = None):
    """Return stations as GeoJSON FeatureCollection."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if city:
            rows = await conn.fetch("""
                SELECT station_id, name, city,
                       ST_AsGeoJSON(geom)::json AS geometry
                FROM stations WHERE city = $1
            """, city)
        else:
            rows = await conn.fetch("""
                SELECT station_id, name, city,
                       ST_AsGeoJSON(geom)::json AS geometry
                FROM stations
            """)
    features = [
        {
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {"id": r["station_id"], "name": r["name"], "city": r["city"]},
        }
        for r in rows
        if r["geometry"]
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/stops")
async def stops(city: str):
    """Return GTFS transit stops for a city as GeoJSON."""
    parquet_map = {
        "stockholm": STOPS_DIR / "stockholm_stops.parquet",
        "amsterdam": STOPS_DIR / "amsterdam_stops.parquet",
    }
    if city not in parquet_map:
        raise HTTPException(400, f"city must be one of {list(parquet_map)}")
    path = parquet_map[city]
    if not path.exists():
        raise HTTPException(404, f"Stops not yet processed for {city}")

    import geopandas as gpd
    gdf = gpd.read_parquet(path)
    return json.loads(gdf.to_json())


@app.get("/api/accessibility")
async def accessibility(city: str):
    """Return WLC accessibility GeoJSON for a city."""
    path = PROCESSED / f"{city}_accessibility.geojson"
    if not path.exists():
        raise HTTPException(404, f"Accessibility data not found for {city}")
    return json.loads(path.read_text())


@app.get("/api/accessibility/stats")
async def accessibility_stats(city: str):
    """Return accessibility summary statistics."""
    path = PROCESSED / f"{city}_accessibility_stats.json"
    if not path.exists():
        raise HTTPException(404, f"Stats not found for {city}")
    return json.loads(path.read_text())


@app.get("/api/tiles/stops/{z}/{x}/{y}.mvt")
async def stops_mvt(z: int, x: int, y: int, city: str = "stockholm"):
    """Serve transit stops as Mapbox Vector Tiles using PostGIS ST_AsMVT."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT ST_AsMVT(q, 'stops', 4096, 'geom') AS mvt
            FROM (
                SELECT
                    stop_id,
                    stop_name,
                    city,
                    ST_AsMVTGeom(
                        ST_Transform(geom, 3857),
                        ST_TileEnvelope($1, $2, $3),
                        4096, 64, true
                    ) AS geom
                FROM transit_stops
                WHERE city = $4
                  AND geom && ST_Transform(ST_TileEnvelope($1, $2, $3), 4326)
            ) q
        """, z, x, y, city)
    mvt = bytes(row["mvt"]) if row and row["mvt"] else b""
    return Response(content=mvt, media_type="application/x-protobuf")


# ── Austin O-D analysis ───────────────────────────────────────────────────────

@app.get("/api/districts/austin")
async def austin_districts():
    """Austin council districts as GeoJSON with trip count via spatial join."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                d.district_id,
                ST_AsGeoJSON(d.geom)::json AS geometry,
                ST_AsGeoJSON(d.centroid)::json AS centroid,
                COUNT(t.id) AS trip_count
            FROM austin_districts d
            LEFT JOIN mobility_trips t
                ON t.city = 'austin'
               AND ST_Within(t.origin_geom, d.geom)
            GROUP BY d.district_id, d.geom, d.centroid
            ORDER BY d.district_id
        """)
    features = [
        {
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {
                "district_id": r["district_id"],
                "trip_count": r["trip_count"],
                "centroid": r["centroid"],
            },
        }
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/od/austin")
async def austin_od_flows():
    """Top 30 Austin O-D flows between council districts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                council_district_start         AS from_district,
                council_district_end           AS to_district,
                COUNT(*)                       AS flow_count,
                AVG(origin_lat)                AS from_lat,
                AVG(origin_lng)                AS from_lng,
                AVG(dest_lat)                  AS to_lat,
                AVG(dest_lng)                  AS to_lng
            FROM mobility_trips
            WHERE city = 'austin'
              AND council_district_start IS NOT NULL
              AND council_district_end   IS NOT NULL
              AND council_district_start != council_district_end
              AND origin_lat IS NOT NULL
            GROUP BY council_district_start, council_district_end
            ORDER BY flow_count DESC
            LIMIT 30
        """)
    return [dict(r) for r in rows]


@app.get("/api/trips/breakdown")
async def trips_breakdown(city: str = "austin"):
    """Vehicle type, monthly, and hourly breakdown for a city."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        by_vehicle = await conn.fetch("""
            SELECT vehicle_type, COUNT(*) AS count
            FROM mobility_trips
            WHERE city = $1 AND vehicle_type IS NOT NULL
            GROUP BY vehicle_type ORDER BY count DESC
        """, city)
        by_month = await conn.fetch("""
            SELECT EXTRACT(MONTH FROM start_time)::int AS month,
                   COUNT(*) AS count
            FROM mobility_trips
            WHERE city = $1 AND start_time IS NOT NULL
            GROUP BY 1 ORDER BY 1
        """, city)
        by_hour = await conn.fetch("""
            SELECT EXTRACT(HOUR FROM start_time)::int AS hour,
                   COUNT(*) AS count
            FROM mobility_trips
            WHERE city = $1 AND start_time IS NOT NULL
            GROUP BY 1 ORDER BY 1
        """, city)
    return {
        "city": city,
        "by_vehicle": [dict(r) for r in by_vehicle],
        "by_month":   [dict(r) for r in by_month],
        "by_hour":    [dict(r) for r in by_hour],
    }


# ── Chicago analysis ──────────────────────────────────────────────────────────

@app.get("/api/districts/chicago")
async def chicago_wards():
    """Chicago wards as GeoJSON."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT ward_id, ST_AsGeoJSON(geom)::json AS geometry
            FROM chicago_wards
        """)
    features = [
        {"type": "Feature", "geometry": r["geometry"],
         "properties": {"ward_id": r["ward_id"]}}
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/od/chicago")
async def chicago_od_flows():
    """Top 30 Chicago Divvy station-to-station flows."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                from_station_id, to_station_id,
                COUNT(*) AS flow_count,
                AVG(from_lat) AS from_lat,
                AVG(from_lng) AS from_lng,
                AVG(to_lat)   AS to_lat,
                AVG(to_lng)   AS to_lng
            FROM chicago_trips
            WHERE from_station_id IS NOT NULL
              AND to_station_id   IS NOT NULL
              AND from_station_id != to_station_id
              AND from_lat IS NOT NULL
              AND to_lat   IS NOT NULL
            GROUP BY 1,2
            ORDER BY flow_count DESC
            LIMIT 30
        """)
    return [dict(r) for r in rows]


@app.get("/api/metro/chicago")
async def chicago_metro():
    """CTA L train lines as GeoJSON."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT line_name, color, ST_AsGeoJSON(geom)::json AS geometry
            FROM chicago_metro_lines
        """)
    features = [
        {"type": "Feature",
         "geometry": r["geometry"],
         "properties": {"line": r["line_name"], "color": r["color"]}}
        for r in rows
    ]
    return {"type": "FeatureCollection", "features": features}


@app.get("/api/trips/summary/chicago")
async def chicago_trips_summary():
    """Chicago Divvy trip stats."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) AS trip_count,
                ROUND(AVG(duration_sec)::numeric / 60, 1) AS avg_duration_min,
                COUNT(DISTINCT from_station_id) AS active_stations
            FROM chicago_trips
        """)
    return dict(row)


# ── Network-based walking catchment ──────────────────────────────────────────

def _nearest_node(G, lat: float, lng: float):
    """Return nearest graph node to (lat, lng) using numpy L2 distance."""
    import numpy as np
    node_ids = list(G.nodes())
    ys = np.array([G.nodes[n]["y"] for n in node_ids])
    xs = np.array([G.nodes[n]["x"] for n in node_ids])
    # Scale lng difference by cos(lat) so distances are isotropic in degrees
    import math
    cos_lat = math.cos(math.radians(lat))
    dists = np.sqrt((ys - lat) ** 2 + ((xs - lng) * cos_lat) ** 2)
    return node_ids[int(np.argmin(dists))]


@app.get("/api/catchment")
async def catchment(
    lat: float,
    lng: float,
    city: str = "stockholm",
    radius_m: float = 500,
):
    """Road edges reachable within radius_m metres of walking from (lat, lng)."""
    G = getattr(app.state, "osm_graphs", {}).get(city)
    if G is None:
        return {"type": "FeatureCollection", "features": []}

    nearest_node = _nearest_node(G, lat, lng)

    reachable_lengths = nx.single_source_dijkstra_path_length(
        G, nearest_node, cutoff=radius_m, weight="length"
    )
    reachable_nodes = set(reachable_lengths.keys())

    features = []
    for u, v, data in G.edges(data=True):
        if u not in reachable_nodes or v not in reachable_nodes:
            continue
        geom = data.get("geometry")
        if geom:
            coords = list(geom.coords)
        else:
            coords = [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"length_m": data.get("length", 0)},
        })

    return {"type": "FeatureCollection", "features": features}
