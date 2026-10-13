"""Transit accessibility scoring — WLC method."""

import json
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import box, Point
from pathlib import Path
try:
    from scipy.spatial import cKDTree as _cKDTree
    _USE_SCIPY = True
except ImportError:
    _USE_SCIPY = False

STOPS_DIR = Path("pipelines/data/processed")
POP_DIR = Path("spatial/data/raw")
OUT = Path("spatial/data/processed")
OUT.mkdir(parents=True, exist_ok=True)

CITY_CONFIG = {
    "stockholm": {
        "bbox": (17.75, 59.20, 18.30, 59.45),
        "stops_parquet": STOPS_DIR / "stockholm_stops.parquet",
        "cell_size_deg": 0.005,
        "raster": POP_DIR / "worldpop_swe_2020.tif",
    },
    "amsterdam": {
        "bbox": (4.72, 52.27, 5.08, 52.44),
        "stops_parquet": STOPS_DIR / "amsterdam_stops.parquet",
        "cell_size_deg": 0.005,
        "raster": POP_DIR / "worldpop_nld_2020.tif",
    },
}

WEIGHTS = {"transit": 0.7, "density": 0.3}


def make_grid(bbox: tuple, cell_size: float) -> gpd.GeoDataFrame:
    """Create a regular grid of square cells over the bounding box."""
    minx, miny, maxx, maxy = bbox
    xs = np.arange(minx, maxx, cell_size)
    ys = np.arange(miny, maxy, cell_size)
    cells = []
    for x in xs:
        for y in ys:
            cells.append(box(x, y, x + cell_size, y + cell_size))
    return gpd.GeoDataFrame(geometry=cells, crs="EPSG:4326")


def _nearest_distances(centroids: np.ndarray, stop_coords: np.ndarray) -> np.ndarray:
    """Return distance to nearest stop for each centroid (degrees)."""
    if _USE_SCIPY:
        tree = _cKDTree(stop_coords)
        dists, _ = tree.query(centroids, k=1)
        return dists
    # numpy fallback: broadcast pairwise distances, take row-wise min
    # safe for grid sizes up to ~10k × ~10k (chunked to limit memory)
    chunk = 500
    dists = np.empty(len(centroids))
    for i in range(0, len(centroids), chunk):
        c = centroids[i : i + chunk, np.newaxis, :]   # (chunk, 1, 2)
        s = stop_coords[np.newaxis, :, :]              # (1, N_stops, 2)
        dists[i : i + chunk] = np.sqrt(((c - s) ** 2).sum(-1)).min(-1)
    return dists


def score_transit(grid: gpd.GeoDataFrame, stops: gpd.GeoDataFrame) -> np.ndarray:
    """Score each cell by inverse distance to nearest transit stop (0–1)."""
    centroids = np.array([[g.centroid.x, g.centroid.y] for g in grid.geometry])
    stop_coords = np.array([[g.x, g.y] for g in stops.geometry])

    dists = _nearest_distances(centroids, stop_coords)
    dists_m = dists * 111_000

    max_dist = 1500.0
    score = np.clip(1 - dists_m / max_dist, 0, 1)
    return score


def score_density(grid: gpd.GeoDataFrame, raster_path: Path) -> np.ndarray:
    """Score each cell by population density from WorldPop raster via zonal_stats."""
    from rasterstats import zonal_stats

    stats = zonal_stats(
        grid.geometry,
        str(raster_path),
        stats=["mean"],
        nodata=-99999,
    )

    raw_values = np.array(
        [s["mean"] if s["mean"] is not None else 0.0 for s in stats],
        dtype=float,
    )

    max_val = raw_values.max()
    if max_val > 0:
        return raw_values / max_val
    return np.zeros_like(raw_values)


def compute_wlc(city: str) -> gpd.GeoDataFrame:
    """Run WLC accessibility scoring for a city."""
    cfg = CITY_CONFIG[city]

    if not cfg["stops_parquet"].exists():
        print(f"  {city}: stops parquet not found — skip")
        return gpd.GeoDataFrame()

    stops = gpd.read_parquet(cfg["stops_parquet"])
    grid = make_grid(cfg["bbox"], cfg["cell_size_deg"])
    print(f"  {city}: {len(grid):,} grid cells, {len(stops):,} stops")

    t_score = score_transit(grid, stops)
    d_score = score_density(grid, cfg["raster"])

    wlc = WEIGHTS["transit"] * t_score + WEIGHTS["density"] * d_score

    grid["transit_score"] = t_score.round(4)
    grid["density_score"] = d_score.round(4)
    grid["accessibility"] = wlc.round(4)
    grid["city"] = city

    stats = {
        "city": city,
        "cell_count": len(grid),
        "stop_count": len(stops),
        "accessibility_mean": float(wlc.mean().round(4)),
        "accessibility_p90": float(np.percentile(wlc, 90).round(4)),
        "high_access_cells": int((wlc >= 0.7).sum()),
        "low_access_cells": int((wlc < 0.3).sum()),
    }

    out_geojson = OUT / f"{city}_accessibility.geojson"
    out_stats = OUT / f"{city}_accessibility_stats.json"

    grid.to_file(out_geojson, driver="GeoJSON")
    out_stats.write_text(json.dumps(stats, indent=2))

    print(f"  mean accessibility: {stats['accessibility_mean']}")
    print(f"  high-access cells (>=0.7): {stats['high_access_cells']:,}")
    print(f"  saved: {out_geojson.name}")
    return grid


if __name__ == "__main__":
    for city in ["stockholm", "amsterdam"]:
        print(f"\n{city.upper()}:")
        compute_wlc(city)
