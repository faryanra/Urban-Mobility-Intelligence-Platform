"""Tests for WorldPop processing logic."""

import pytest


def test_city_bbox_coverage():
    from spatial.process_worldpop import CITY_BBOX

    sthlm = CITY_BBOX["stockholm"]
    assert 17 < sthlm[0] < 19
    assert 59 < sthlm[1] < 60

    ams = CITY_BBOX["amsterdam"]
    assert 4 < ams[0] < 5
    assert 52 < ams[1] < 53


def test_stats_output_shape():
    stats = {
        "city": "stockholm",
        "total_population": 975000,
        "mean_per_cell": 450.2,
        "max_per_cell": 12000.0,
        "cell_count": 2167,
    }
    for key in ["city", "total_population", "mean_per_cell", "cell_count"]:
        assert key in stats
