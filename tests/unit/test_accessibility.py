"""Tests for WLC accessibility scoring."""

import numpy as np
import pytest
import geopandas as gpd
from shapely.geometry import Point, box


def test_make_grid_cell_count():
    from spatial.accessibility import make_grid
    grid = make_grid((0.0, 0.0, 0.1, 0.1), cell_size=0.01)
    assert len(grid) == 100


def test_transit_score_decreases_with_distance():
    from spatial.accessibility import score_transit

    stop = gpd.GeoDataFrame(geometry=[Point(0.0, 0.0)], crs="EPSG:4326")
    grid = gpd.GeoDataFrame(
        geometry=[
            box(-0.001, -0.001, 0.001, 0.001),
            box(0.05, 0.05, 0.06, 0.06),
        ],
        crs="EPSG:4326",
    )
    scores = score_transit(grid, stop)
    assert scores[0] > scores[1]


def test_wlc_range():
    scores = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    weights = {"transit": 0.7, "density": 0.3}
    wlc = weights["transit"] * scores + weights["density"] * scores
    assert wlc.min() >= 0.0
    assert wlc.max() <= 1.0
