"""Clip and sample WorldPop raster to city bounding boxes."""

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box, mapping
from pathlib import Path
import json

RAW = Path("spatial/data/raw")
OUT = Path("spatial/data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# City bounding boxes (WGS84): (lon_min, lat_min, lon_max, lat_max)
CITY_BBOX = {
    "stockholm": (17.75, 59.20, 18.30, 59.45),
    "amsterdam": (4.72,  52.27, 5.08,  52.44),
}

RASTER_FILES = {
    "stockholm": RAW / "worldpop_swe_2020.tif",
    "amsterdam": RAW / "worldpop_nld_2020.tif",
}


def clip_to_city(city: str) -> dict:
    """Clip raster to city bbox and return population stats."""
    tif_path = RASTER_FILES[city]
    if not tif_path.exists():
        print(f"  {city}: raster not found — skip")
        return {}

    bbox = CITY_BBOX[city]
    geom = [mapping(box(*bbox))]

    with rasterio.open(tif_path) as src:
        clipped, transform = mask(src, geom, crop=True, nodata=0)
        data = clipped[0]

    data = data[data > 0]

    stats = {
        "city": city,
        "total_population": int(data.sum()),
        "mean_per_cell": float(data.mean()),
        "max_per_cell": float(data.max()),
        "cell_count": int(len(data)),
    }

    out_path = OUT / f"{city}_population_stats.json"
    out_path.write_text(json.dumps(stats, indent=2))
    print(f"  {city}: pop={stats['total_population']:,}, cells={stats['cell_count']:,}")
    return stats


if __name__ == "__main__":
    for city in ["stockholm", "amsterdam"]:
        clip_to_city(city)
