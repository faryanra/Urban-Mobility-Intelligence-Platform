"""Transit accessibility scoring (WLC) on a metric grid, written to PostGIS."""

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from scipy.spatial import cKDTree
from shapely.geometry import box

from pipelines.db import DATABASE_URL

POP_DIR = Path("spatial/data/raw")

CITY_CONFIG = {
    "stockholm": {
        "bbox": (17.75, 59.20, 18.30, 59.45),
        "crs": "EPSG:3006",
        "raster": POP_DIR / "worldpop_swe_2020.tif",
    },
    "amsterdam": {
        "bbox": (4.72, 52.27, 5.08, 52.44),
        "crs": "EPSG:28992",
        "raster": POP_DIR / "worldpop_nld_2020.tif",
    },
}

CELL_SIZE_M = 500
MAX_WALK_M = 1500.0
WEIGHTS = {"transit": 0.7, "density": 0.3}


def make_grid(bbox: tuple, cell_size: float, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """Regular grid of square cells over bbox, in the units of crs."""
    minx, miny, maxx, maxy = bbox
    cells = [
        box(x, y, x + cell_size, y + cell_size)
        for x in np.arange(minx, maxx, cell_size)
        for y in np.arange(miny, maxy, cell_size)
    ]
    return gpd.GeoDataFrame(geometry=cells, crs=crs)


def score_transit(cell_xy: np.ndarray, stop_xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Linear decay on metric distance to the nearest stop: 1 at the stop, 0 at MAX_WALK_M."""
    dists, _ = cKDTree(stop_xy).query(cell_xy, k=1)
    return np.clip(1 - dists / MAX_WALK_M, 0, 1), dists


def score_density(grid_wgs84: gpd.GeoDataFrame, raster_path: Path) -> np.ndarray:
    """Mean WorldPop 100m population per cell, scaled 0-1 by the city maximum."""
    from rasterstats import zonal_stats

    stats = zonal_stats(grid_wgs84.geometry, str(raster_path), stats=["mean"], nodata=-99999)
    raw = np.array([s["mean"] or 0.0 for s in stats], dtype=float)
    peak = raw.max()
    return raw / peak if peak > 0 else np.zeros_like(raw)


def city_grid(city: str) -> gpd.GeoDataFrame:
    cfg = CITY_CONFIG[city]
    area = gpd.GeoSeries([box(*cfg["bbox"])], crs="EPSG:4326").to_crs(cfg["crs"])
    grid = make_grid(tuple(area.total_bounds), CELL_SIZE_M, cfg["crs"])
    return grid[grid.centroid.within(area.iloc[0])].reset_index(drop=True)


def load_stops(conn, city: str, crs: str) -> np.ndarray:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT ST_X(geom), ST_Y(geom) FROM transit_stops WHERE city = %s", (city,)
        )
        rows = cur.fetchall()
    if not rows:
        raise SystemExit(f"No transit stops for {city}; run pipelines.load_stops first")
    pts = gpd.GeoSeries(gpd.points_from_xy(*zip(*rows)), crs="EPSG:4326").to_crs(crs)
    return np.column_stack([pts.x, pts.y])


def compute_wlc(city: str) -> None:
    cfg = CITY_CONFIG[city]
    conn = psycopg2.connect(DATABASE_URL)
    try:
        stop_xy = load_stops(conn, city, cfg["crs"])
        grid = city_grid(city)
        centroids = grid.centroid
        t_score, nearest_m = score_transit(np.column_stack([centroids.x, centroids.y]), stop_xy)

        grid_wgs84 = grid.to_crs("EPSG:4326")
        d_score = score_density(grid_wgs84, cfg["raster"])
        wlc = WEIGHTS["transit"] * t_score + WEIGHTS["density"] * d_score

        rows = [
            (city, round(float(t), 4), round(float(d), 4), round(float(w), 4),
             round(float(m), 1), geom.wkt)
            for t, d, w, m, geom in zip(t_score, d_score, wlc, nearest_m, grid_wgs84.geometry)
        ]
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accessibility_cells WHERE city = %s", (city,))
            execute_values(
                cur,
                """INSERT INTO accessibility_cells
                   (city, transit_score, density_score, accessibility, nearest_stop_m, geom)
                   VALUES %s""",
                rows,
                template="(%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))",
            )
        conn.commit()
    finally:
        conn.close()

    print(f"  {city}: {len(grid):,} cells of {CELL_SIZE_M} m, {len(stop_xy):,} stops")
    print(f"  mean WLC {wlc.mean():.3f}, cells below 0.3: {(wlc < 0.3).sum():,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", choices=list(CITY_CONFIG), action="append")
    for name in parser.parse_args().city or list(CITY_CONFIG):
        print(f"{name.upper()}:")
        compute_wlc(name)
