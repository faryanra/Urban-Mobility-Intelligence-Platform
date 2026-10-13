"""Tests for build_network config and output path logic."""

from pathlib import Path
from pipelines.build_network import CITIES, OUT_DIR


def test_cities_defined():
    assert "stockholm" in CITIES
    assert "amsterdam" in CITIES


def test_cities_have_required_keys():
    for city, cfg in CITIES.items():
        assert "query" in cfg, f"{city} missing query"
        assert "crs" in cfg, f"{city} missing crs"


def test_stockholm_crs():
    assert CITIES["stockholm"]["crs"] == "EPSG:3006"


def test_amsterdam_crs():
    assert CITIES["amsterdam"]["crs"] == "EPSG:28992"


def test_output_paths():
    for city in CITIES:
        expected = OUT_DIR / f"{city}_network.gpkg"
        assert expected.suffix == ".gpkg"
        assert city in expected.name
