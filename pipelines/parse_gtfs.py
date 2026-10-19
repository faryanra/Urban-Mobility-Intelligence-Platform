"""Parse GTFS stops and routes into GeoDataFrame."""

import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

OUT = Path("pipelines/data/processed")
OUT.mkdir(parents=True, exist_ok=True)


CITY_BBOX = {
    "amsterdam": (4.73, 52.27, 5.07, 52.44),
}


def parse_stops(zip_path: Path, city: str) -> gpd.GeoDataFrame:
    """Extract stops.txt from GTFS zip and return GeoDataFrame."""
    with zipfile.ZipFile(zip_path, "r") as z, z.open("stops.txt") as f:
        stops = pd.read_csv(f)

    print(f"  {city}: {len(stops):,} raw stops")

    stops.columns = [c.strip().lower() for c in stops.columns]

    for col in ["stop_id", "stop_lat", "stop_lon"]:
        if col not in stops.columns:
            raise ValueError(f"Missing column: {col} in {zip_path.name}")

    stops = stops.dropna(subset=["stop_lat", "stop_lon"])
    stops = stops[
        stops["stop_lat"].between(-90, 90) &
        stops["stop_lon"].between(-180, 180)
    ]

    gdf = gpd.GeoDataFrame(
        stops,
        geometry=[Point(row.stop_lon, row.stop_lat) for _, row in stops.iterrows()],
        crs="EPSG:4326",
    )

    gdf["city"] = city

    if city in CITY_BBOX:
        minx, miny, maxx, maxy = CITY_BBOX[city]
        gdf = gdf[
            gdf.geometry.x.between(minx, maxx) &
            gdf.geometry.y.between(miny, maxy)
        ]

    print(f"  {city}: {len(gdf):,} valid stops")
    return gdf[["stop_id", "stop_name", "city", "geometry"]]


if __name__ == "__main__":
    sl_zip = Path("pipelines/data/raw/sl_gtfs.zip")
    gvb_zip = Path("pipelines/data/raw/gvb_gtfs.zip")

    if sl_zip.exists():
        print("Stockholm SL:")
        stops_sthlm = parse_stops(sl_zip, "stockholm")
        stops_sthlm.to_parquet(OUT / "stockholm_stops.parquet", index=False)
        print("  saved: stockholm_stops.parquet")
    else:
        print("Stockholm zip not found — skipping")

    if gvb_zip.exists():
        print("Amsterdam GVB:")
        stops_ams = parse_stops(gvb_zip, "amsterdam")
        stops_ams.to_parquet(OUT / "amsterdam_stops.parquet", index=False)
        print("  saved: amsterdam_stops.parquet")
