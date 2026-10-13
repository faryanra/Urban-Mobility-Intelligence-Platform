# Urban Mobility Intelligence Platform

[![CI](https://github.com/faryanra/Urban-Mobility-Intelligence-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/faryanra/Urban-Mobility-Intelligence-Platform/actions)

An interactive geospatial analytics platform comparing transit-first European cities (Stockholm and Amsterdam) with micromobility-dominant American cities (Austin and Chicago) across four real urban datasets.

| Stockholm (European transit + WLC grid) | Austin (US micromobility O-D flows) |
|---|---|
| ![Stockholm view](docs/screenshots/stockholm.webp) | ![Austin view](docs/screenshots/austin.webp) |

## What It Analyzes

**European cities: Stockholm and Amsterdam**

Weighted Location Coverage (WLC) scoring reveals that transit accessibility is not uniform. Outer neighbourhoods consistently score below 0.3, exposing genuine policy gaps. Click any transit stop to visualize the real 500m walking catchment along the road network. This uses actual Dijkstra traversal on the OSMnx walk graph, not a Euclidean buffer.

**American cities: Austin and Chicago**

514,000 Austin micromobility trips cluster in District 9, the downtown core where transit already exists. Chicago's Divvy bike-share origin-destination flows align closely with CTA L train corridors. The pattern is consistent: micromobility supplements transit density, it does not fill gaps.

## Architecture

```mermaid
flowchart TD
    A[Open Data Sources] --> B[Python Pipelines]
    B --> C[(PostGIS 16 + PostGIS 3.4)]
    C --> D[FastAPI + ST_AsMVT]
    D --> E[Next.js 14 + MapLibre GL JS v6]

    subgraph Sources
        A1[Stockholm GTFS / Trafiklab] --> A
        A2[Amsterdam GTFS / OVapi] --> A
        A3[WorldPop 1km raster] --> A
        A4[Austin Open Data trips] --> A
        A5[Chicago Socrata trips] --> A
    end

    subgraph Pipelines
        B1[fetch_gtfs_stockholm.py] --> B
        B2[fetch_gtfs_amsterdam.py] --> B
        B3[load_accessibility.py] --> B
        B4[fetch_austin_trips_v2.py] --> B
        B5[load_chicago_trips.py] --> B
    end
```

## Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 + PostGIS 3.4 (Docker) |
| Pipelines | Python: asyncpg, httpx, rasterstats, OSMnx |
| API | FastAPI + asyncpg, vector tiles via ST_AsMVT |
| Frontend | Next.js 14 + MapLibre GL JS v6 |
| Styling | Tailwind CSS |

## Data Sources

| Dataset | Records | Source |
|---|---|---|
| Stockholm GTFS stops | 21,891 | Trafiklab / SL |
| Amsterdam GTFS stops | 3,215 | OVapi |
| WorldPop 1km raster (SE + NL) | raster | WorldPop Project |
| Austin micromobility trips | 514,000 | City of Austin Open Data |
| Austin council districts | 10 | City of Austin ArcGIS |
| Chicago Divvy trips | 50,000 | City of Chicago Socrata |
| Chicago ward boundaries | 50 | City of Chicago Socrata |
| Chicago CTA L lines | 50 segments | City of Chicago Socrata |

## Key Features

- **H3 hexagonal accessibility grid**: WLC score per cell (transit 70% + population density 30%)
- **Network-based walking catchment**: OSMnx walk graph, Dijkstra traversal with 500m cutoff per click
- **WLC threshold filter**: slider reveals only underserved cells (score below threshold)
- **Hover tooltips**: WLC components, stop names, trip corridor volumes
- **Origin-destination arc flows**: bezier arcs weighted by trip count for Austin (district-to-district) and Chicago (station-to-station)
- **Vector tiles**: 21,891 Stockholm stops delivered as ST_AsMVT binary tiles

## Local Setup

```bash
# 1. Start PostGIS
cd database && docker compose up -d

# 2. Run migrations
psql postgresql://mobility_user:mobility_pass@localhost:5434/mobility_db \
  -f migrations/001_schema.sql \
  -f migrations/002_stops.sql \
  -f migrations/003_city_geo.sql \
  -f migrations/004_austin_od_columns.sql

# 3. Run data pipelines
python pipelines/fetch_gtfs_stockholm.py
python pipelines/fetch_gtfs_amsterdam.py
python pipelines/load_accessibility.py --city stockholm
python pipelines/load_accessibility.py --city amsterdam
python pipelines/fetch_austin_districts.py
python pipelines/fetch_austin_trips_v2.py
python pipelines/fetch_chicago_geo.py
python pipelines/load_chicago_trips.py

# 4. Build OSM walk graph cache (one-time, ~60MB per city)
python pipelines/build_osm_cache.py

# 5. Start API
cd api && uvicorn main:app --port 8001 --reload

# 6. Start frontend
cd frontend && npm run dev
```

## WLC Methodology

```
score = 0.7 x transit_score + 0.3 x population_score
transit_score = stops within 500m radius / max(city stops)
population_score = zonal_stats(H3 polygon, WorldPop 1km raster, "mean")
normalized 0-1 within city
```

## CI

GitHub Actions runs on every push to `main`:

- **backend**: PostGIS service container, applies all 4 migrations, ruff lint, pytest (25 tests)
- **frontend**: Node 20, npm install, TypeScript type-check, Next.js build
