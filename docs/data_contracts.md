# Data Contracts

## Austin — Shared Micromobility Vehicle Trips
- Source: https://data.austintexas.gov/Transportation-and-Mobility/Shared-Micromobility-Vehicle-Trips/7d8e-dm7r
- Format: CSV
- Key columns: ID, Trip Duration, Trip Distance, Start Time, End Time, Origin Cell ID, Destination Cell ID, Vehicle Type
- CRS: WGS84 (EPSG:4326)
- Local path (not committed): pipelines/data/raw/austin_trips.csv

## Chicago — Divvy Bike Share
- Source: https://divvy-tripdata.s3.amazonaws.com/index.html (Divvy_Trips_2013_Jun.csv)
- Format: CSV
- Key columns: TRIP DURATION, FROM STATION ID, TO STATION ID, START TIME, STOP TIME, FROM LATITUDE, FROM LONGITUDE, TO LATITUDE, TO LONGITUDE
- CRS: WGS84 (EPSG:4326)
- Local path (not committed): pipelines/data/raw/chicago_divvy_2013_jun.csv

## Stockholm — Road Network
- Source: OpenStreetMap via OSMnx query: "Stockholm, Sweden"
- Fetched at runtime, not stored
- Script: pipelines/fetch_network.py (Phase 3)
- Analysis CRS: EPSG:3006 (SWEREF99 TM)

## Amsterdam — Road Network
- Source: OpenStreetMap via OSMnx query: "Amsterdam, Netherlands"
- Fetched at runtime, not stored
- Script: pipelines/fetch_network.py (Phase 3)
- Analysis CRS: EPSG:28992 (RD New)

## Stockholm — Transit (SL GTFS)
- Source: https://www.trafiklab.se/api/gtfs-regional/
- Registration required (free)
- Key files: stops.txt, routes.txt, stop_times.txt
- Local path (not committed): pipelines/data/raw/sl_gtfs/

## Amsterdam — Transit (GVB GTFS)
- Source: https://openov.nl or https://www.ov-chipkaart.nl/open-data
- Key files: stops.txt, routes.txt
- Local path (not committed): pipelines/data/raw/gvb_gtfs/

## Population — WorldPop
- Source: https://hub.worldpop.org/geodata/listing?id=76
- Format: GeoTIFF, 100m resolution
- CRS: WGS84 (EPSG:4326)
- Local path (not committed): spatial/data/raw/worldpop_europe_2020.tif
