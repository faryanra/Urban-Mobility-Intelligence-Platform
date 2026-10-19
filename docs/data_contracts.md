# Data Contracts

All raw and intermediate files live under `pipelines/data/` or `spatial/data/` and are never committed.
Everything is stored in PostGIS as EPSG:4326. Metric analysis uses EPSG:3006 (Stockholm) and EPSG:28992 (Amsterdam).

## Stockholm transit stops (SL GTFS)
- Source: Trafiklab GTFS Regional, `https://opendata.samtrafiken.se/gtfs/sl/sl.zip` (free API key)
- Script: `pipelines/fetch_gtfs.py <key>` then `pipelines/parse_gtfs.py`
- Local path: `pipelines/data/raw/sl_gtfs.zip`, `pipelines/data/processed/stockholm_stops.parquet`
- Table: `transit_stops` (21,891 stops, whole SL region)

## Amsterdam transit stops (GTFS NL)
- Source: OVapi national feed, `https://gtfs.ovapi.nl/nl/gtfs-nl.zip`
- Script: `pipelines/fetch_gtfs.py`, `pipelines/parse_gtfs.py` (clipped to the Amsterdam bounding box)
- Local path: `pipelines/data/raw/gvb_gtfs.zip`, `pipelines/data/processed/amsterdam_stops.parquet`
- Table: `transit_stops` (3,215 stops)

## Population (WorldPop)
- Source: WorldPop Global 2000-2020, 2020 people-per-pixel, 100 m resolution (`swe_ppp_2020.tif`, `nld_ppp_2020.tif`)
- Script: `pipelines/fetch_worldpop.py`
- Local path: `spatial/data/raw/worldpop_{swe,nld}_2020.tif`
- Used by: `spatial/accessibility.py` (zonal mean per grid cell)

## Accessibility grid (derived)
- Script: `spatial/accessibility.py`
- Table: `accessibility_cells` (500 m square cells built in the metric CRS)
- Columns: `transit_score`, `density_score`, `accessibility`, `nearest_stop_m`

## Walking network (OpenStreetMap)
- Source: OSMnx `graph_from_place(..., network_type="walk")` for "Stockholm, Sweden" and "Amsterdam, Netherlands"
- Script: `pipelines/build_osm_cache.py`
- Local path: `api/data/osm_cache/{city}_walk.graphml` (read by the API for walking catchments)

## Austin shared micromobility trips
- Source: City of Austin Socrata dataset `7d8e-dm7r`
- Scripts: `pipelines/fetch_austin_trips.py` (first 50,000 rows), `pipelines/clean_austin.py`, `pipelines/load_austin.py`, `pipelines/map_austin_districts.py`
- Table: `mobility_trips` (48,200 trips after cleaning, 9 to 12 Oct 2021 local time)
- Timestamps are stored in UTC and converted to America/Chicago in the API
- Trip ends are published by council district only; `origin_*`/`dest_*` hold district centroids

## Austin council districts
- Source: City of Austin ArcGIS `BOUNDARIES_single_member_districts`
- Scripts: `pipelines/fetch_austin_districts.py`, `pipelines/load_austin_districts.py`
- Table: `austin_districts` (10 districts)

## Chicago Divvy trips
- Source: City of Chicago Socrata dataset `fg6s-gzvg`
- Scripts: `pipelines/fetch_chicago_trips.py` (50,000 rows), `pipelines/load_chicago_trips.py`
- Local path: `pipelines/data/raw/chicago_divvy_trips_june2013.csv`
- Table: `chicago_trips` (27 Jun to 21 Jul 2013, 120 stations)

## Chicago wards and CTA L lines
- Source: City of Chicago Socrata datasets `p293-wvbd` (wards) and `xbyr-jnvx` (L line segments)
- Scripts: `pipelines/fetch_chicago_geo.py`, `pipelines/load_chicago_geo.py`
- Tables: `chicago_wards` (50), `chicago_metro_lines` (153 segments)
