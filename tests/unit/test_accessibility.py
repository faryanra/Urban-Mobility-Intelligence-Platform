"""Tests for WLC accessibility scoring."""

import numpy as np


def test_make_grid_cell_count():
    from spatial.accessibility import make_grid
    grid = make_grid((0.0, 0.0, 0.1, 0.1), cell_size=0.01)
    assert len(grid) == 100


def test_make_grid_metric_crs():
    from spatial.accessibility import make_grid
    grid = make_grid((0, 0, 2000, 1000), cell_size=500, crs="EPSG:3006")
    assert len(grid) == 8
    assert grid.crs.to_epsg() == 3006
    assert np.allclose(grid.area, 500 * 500)


def test_transit_score_uses_metres():
    from spatial.accessibility import MAX_WALK_M, score_transit
    stops = np.array([[0.0, 0.0]])
    cells = np.array([[0.0, 0.0], [300.0, 400.0], [MAX_WALK_M + 1, 0.0]])
    scores, dists = score_transit(cells, stops)
    assert np.allclose(dists, [0.0, 500.0, MAX_WALK_M + 1])
    assert scores[0] == 1.0
    assert np.isclose(scores[1], 1 - 500 / MAX_WALK_M)
    assert scores[2] == 0.0


def test_city_grid_is_metric():
    from spatial.accessibility import CELL_SIZE_M, city_grid
    grid = city_grid("stockholm")
    assert grid.crs.to_epsg() == 3006
    assert np.allclose(grid.area, CELL_SIZE_M ** 2)
    assert 2000 < len(grid) < 5000


def test_wlc_weights_sum_to_one():
    from spatial.accessibility import WEIGHTS
    assert sum(WEIGHTS.values()) == 1.0
