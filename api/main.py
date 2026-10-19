"""Urban Mobility Intelligence Platform REST API."""

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from threading import Lock
from typing import Literal

import networkx as nx
import numpy as np
import osmnx as ox
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response
from scipy.spatial import cKDTree

from api.config import CORS_ORIGINS, OSM_CACHE_DIR
from api.database import close_pool, get_pool

EuCity = Literal["stockholm", "amsterdam"]
EU_CITIES: tuple[str, ...] = ("stockholm", "amsterdam")
AUSTIN_TZ = "America/Chicago"
CACHE_TTL_S = 3600


# Static analytical data only changes when pipelines rerun, so results are memoised.
_cache: dict[str, tuple[float, object]] = {}


async def cached(key: str, compute: Callable[[], Awaitable[object]]):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    value = await compute()
    _cache[key] = (time.monotonic(), value)
    return value


class WalkGraph:
    """OSM walk network with a KD-tree over node coordinates for nearest-node lookup."""

    def __init__(self, G: nx.MultiDiGraph):
        self.G = G
        self.nodes = list(G.nodes)
        ys = np.array([G.nodes[n]["y"] for n in self.nodes])
        xs = np.array([G.nodes[n]["x"] for n in self.nodes])
        self.cos_lat = math.cos(math.radians(float(ys.mean())))
        self.tree = cKDTree(np.column_stack([xs * self.cos_lat, ys]))

    def nearest(self, lat: float, lng: float):
        _, i = self.tree.query([lng * self.cos_lat, lat])
        return self.nodes[int(i)]


_graphs: dict[str, WalkGraph | None] = {}
_graph_lock = Lock()


def walk_graph(city: str) -> WalkGraph | None:
    with _graph_lock:
        if city not in _graphs:
            path = OSM_CACHE_DIR / f"{city}_walk.graphml"
            _graphs[city] = WalkGraph(ox.load_graphml(path)) if path.exists() else None
        return _graphs[city]


def _preload_graphs() -> None:
    for city in EU_CITIES:
        walk_graph(city)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    preload = asyncio.create_task(asyncio.to_thread(_preload_graphs))
    yield
    preload.cancel()
    await close_pool()


app = FastAPI(title="Urban Mobility Intelligence Platform", version="1.1.0", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


async def _fetch(sql: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def _fetchrow(sql: str, *args):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


@app.get("/health")
async def health():
    row = await _fetchrow("SELECT version()")
    return {"status": "ok", "db": row["version"][:30]}


@app.get("/api/trips/summary")
async def trips_summary():
    """Trip count and average duration per city in mobility_trips."""
    rows = await _fetch("""
        SELECT city, COUNT(*) AS trip_count, AVG(duration_sec) AS avg_duration_sec
        FROM mobility_trips
        GROUP BY city
        ORDER BY city
    """)
    return [dict(r) for r in rows]


# ── European accessibility ────────────────────────────────────────────────────

@app.get("/api/accessibility")
async def accessibility(city: EuCity):
    """WLC accessibility grid for a city as a GeoJSON FeatureCollection."""
    async def compute():
        row = await _fetchrow("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(json_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom, 6)::json,
                    'properties', json_build_object(
                        'accessibility', accessibility,
                        'transit_score', transit_score,
                        'density_score', density_score,
                        'nearest_stop_m', nearest_stop_m
                    )
                )), '[]'::json)
            )::text AS fc
            FROM accessibility_cells
            WHERE city = $1
        """, city)
        return row["fc"]

    return Response(await cached(f"accessibility:{city}", compute), media_type="application/json")


@app.get("/api/accessibility/stats")
async def accessibility_stats(city: EuCity):
    """Summary statistics of the WLC grid for a city."""
    async def compute():
        row = await _fetchrow("""
            SELECT
                COUNT(*)                                          AS cell_count,
                COALESCE(AVG(accessibility), 0)                   AS accessibility_mean,
                COUNT(*) FILTER (WHERE accessibility >= 0.7)      AS high_access_cells,
                COUNT(*) FILTER (WHERE accessibility < 0.3)       AS low_access_cells,
                COUNT(*) FILTER (WHERE nearest_stop_m > 500)      AS cells_beyond_500m,
                (SELECT COUNT(*) FROM transit_stops WHERE city = $1) AS stop_count
            FROM accessibility_cells
            WHERE city = $1
        """, city)
        return dict(row)

    stats = await cached(f"accessibility_stats:{city}", compute)
    if stats["cell_count"] == 0:
        raise HTTPException(404, f"Accessibility grid not loaded for {city}")
    return stats


@app.get("/api/tiles/stops/{z}/{x}/{y}.mvt")
async def stops_mvt(z: int, x: int, y: int, city: EuCity = "stockholm"):
    """Transit stops as Mapbox Vector Tiles built with ST_AsMVT."""
    row = await _fetchrow("""
        SELECT ST_AsMVT(q, 'stops', 4096, 'geom') AS mvt
        FROM (
            SELECT
                stop_id,
                stop_name,
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
    return Response(
        content=mvt,
        media_type="application/x-protobuf",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/catchment")
def catchment(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    city: EuCity = "stockholm",
    radius_m: float = Query(500, gt=0, le=2000),
):
    """Street segments reachable within radius_m metres of walking from (lat, lng)."""
    graph = walk_graph(city)
    if graph is None:
        raise HTTPException(503, "Walking network is not available on this server")

    G = graph.G
    reachable = nx.single_source_dijkstra_path_length(
        G, graph.nearest(lat, lng), cutoff=radius_m, weight="length"
    )

    features = []
    for u, v, data in G.subgraph(reachable).edges(data=True):
        geom = data.get("geometry")
        coords = (
            list(geom.coords) if geom is not None
            else [(G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
        )
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"length_m": data.get("length", 0)},
        })
    return {"type": "FeatureCollection", "features": features}


# ── Austin ────────────────────────────────────────────────────────────────────

@app.get("/api/districts/austin")
async def austin_districts():
    """Austin council districts with trip counts by origin district."""
    async def compute():
        rows = await _fetch("""
            SELECT
                d.district_id,
                ST_AsGeoJSON(d.geom, 6)::json   AS geometry,
                ST_AsGeoJSON(d.centroid)::json  AS centroid,
                COUNT(t.id)                     AS trip_count
            FROM austin_districts d
            LEFT JOIN mobility_trips t
                ON t.city = 'austin'
               AND t.council_district_start = d.district_id
            GROUP BY d.district_id, d.geom, d.centroid
            ORDER BY d.district_id
        """)
        return {
            "type": "FeatureCollection",
            "features": [
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
            ],
        }

    return await cached("austin_districts", compute)


@app.get("/api/od/austin")
async def austin_od_flows():
    """Top 30 Austin district-to-district flows; endpoints are district centroids."""
    async def compute():
        rows = await _fetch("""
            SELECT
                council_district_start  AS from_district,
                council_district_end    AS to_district,
                COUNT(*)                AS flow_count,
                AVG(origin_lat)         AS from_lat,
                AVG(origin_lng)         AS from_lng,
                AVG(dest_lat)           AS to_lat,
                AVG(dest_lng)           AS to_lng
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

    return await cached("austin_od", compute)


@app.get("/api/trips/breakdown")
async def trips_breakdown(city: Literal["austin"] = "austin"):
    """Vehicle type and local-time hourly breakdown, plus the covered date range."""
    async def compute():
        pool = await get_pool()
        async with pool.acquire() as conn:
            by_vehicle = await conn.fetch("""
                SELECT vehicle_type, COUNT(*) AS count
                FROM mobility_trips
                WHERE city = $1 AND vehicle_type IS NOT NULL
                GROUP BY vehicle_type ORDER BY count DESC
            """, city)
            by_hour = await conn.fetch("""
                SELECT EXTRACT(HOUR FROM start_time AT TIME ZONE $2)::int AS hour,
                       COUNT(*) AS count
                FROM mobility_trips
                WHERE city = $1 AND start_time IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """, city, AUSTIN_TZ)
            period = await conn.fetchrow("""
                SELECT MIN(start_time AT TIME ZONE $2)::date AS start,
                       MAX(start_time AT TIME ZONE $2)::date AS end
                FROM mobility_trips
                WHERE city = $1
            """, city, AUSTIN_TZ)
        return {
            "city": city,
            "timezone": AUSTIN_TZ,
            "period": {k: (v.isoformat() if v else None) for k, v in period.items()},
            "by_vehicle": [dict(r) for r in by_vehicle],
            "by_hour": [dict(r) for r in by_hour],
        }

    return await cached(f"breakdown:{city}", compute)


# ── Chicago ───────────────────────────────────────────────────────────────────

@app.get("/api/districts/chicago")
async def chicago_wards():
    """Chicago wards as GeoJSON."""
    async def compute():
        rows = await _fetch(
            "SELECT ward_id, ST_AsGeoJSON(geom, 6)::json AS geometry FROM chicago_wards"
        )
        return {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": r["geometry"],
                 "properties": {"ward_id": r["ward_id"]}}
                for r in rows
            ],
        }

    return await cached("chicago_wards", compute)


@app.get("/api/od/chicago")
async def chicago_od_flows():
    """Top 30 Chicago Divvy station-to-station flows."""
    async def compute():
        rows = await _fetch("""
            SELECT
                from_station_id, to_station_id,
                MAX(from_station_name) AS from_station_name,
                MAX(to_station_name)   AS to_station_name,
                COUNT(*)      AS flow_count,
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
            GROUP BY 1, 2
            ORDER BY flow_count DESC
            LIMIT 30
        """)
        return [dict(r) for r in rows]

    return await cached("chicago_od", compute)


@app.get("/api/metro/chicago")
async def chicago_metro():
    """CTA L train lines as GeoJSON."""
    async def compute():
        rows = await _fetch(
            "SELECT line_name, color, ST_AsGeoJSON(geom, 6)::json AS geometry"
            " FROM chicago_metro_lines"
        )
        return {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": r["geometry"],
                 "properties": {"line": r["line_name"], "color": r["color"]}}
                for r in rows
            ],
        }

    return await cached("chicago_metro", compute)


@app.get("/api/trips/summary/chicago")
async def chicago_trips_summary():
    """Chicago Divvy trip count, median duration, stations used and date range."""
    async def compute():
        row = await _fetchrow("""
            SELECT
                COUNT(*) AS trip_count,
                COALESCE(ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_sec)
                                / 60)::numeric, 1), 0)::float AS median_duration_min,
                (SELECT COUNT(*) FROM (
                    SELECT from_station_id FROM chicago_trips
                    UNION SELECT to_station_id FROM chicago_trips
                ) s) AS active_stations,
                MIN(start_time)::date AS period_start,
                MAX(start_time)::date AS period_end
            FROM chicago_trips
        """)
        return dict(row)

    return await cached("chicago_summary", compute)


@app.get("/api/stations/chicago")
async def chicago_stations():
    """Divvy stations used by the trip sample, located from the trip records."""
    async def compute():
        rows = await _fetch("""
            SELECT id, MAX(name) AS name, AVG(lat) AS lat, AVG(lng) AS lng,
                   SUM(departure) AS departures
            FROM (
                SELECT from_station_id AS id, from_station_name AS name,
                       from_lat AS lat, from_lng AS lng, 1 AS departure
                FROM chicago_trips
                UNION ALL
                SELECT to_station_id, to_station_name, to_lat, to_lng, 0
                FROM chicago_trips
            ) s
            WHERE id IS NOT NULL AND lat IS NOT NULL AND lng IS NOT NULL
            GROUP BY id
        """)
        return {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
                 "properties": {"id": r["id"], "name": r["name"], "departures": r["departures"]}}
                for r in rows
            ],
        }

    return await cached("chicago_stations", compute)
