"""Tests for GTFS parsing logic."""

import io
import zipfile
from pathlib import Path

import pytest

from pipelines.parse_gtfs import parse_stops


def make_fake_gtfs_zip(stops_csv: str) -> Path:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("stops.txt", stops_csv)
    buf.seek(0)
    tmp = Path("/tmp/test_gtfs.zip")
    tmp.write_bytes(buf.read())
    return tmp


VALID_STOPS_CSV = """stop_id,stop_name,stop_lat,stop_lon
1,Central Station,59.3301,18.0586
2,Gamla Stan,59.3232,18.0710
3,Slussen,59.3193,18.0723
"""

INVALID_STOPS_CSV = """stop_id,stop_name,stop_lat,stop_lon
1,Bad Stop,999,200
2,Good Stop,59.33,18.05
"""


def test_parse_stops_valid():
    path = make_fake_gtfs_zip(VALID_STOPS_CSV)
    gdf = parse_stops(path, "stockholm")
    assert len(gdf) == 3
    assert "geometry" in gdf.columns
    assert gdf.crs.to_epsg() == 4326


def test_parse_stops_filters_invalid_coords():
    path = make_fake_gtfs_zip(INVALID_STOPS_CSV)
    gdf = parse_stops(path, "stockholm")
    assert len(gdf) == 1


def test_parse_stops_missing_column():
    bad_csv = "stop_id,stop_name\n1,No Coords\n"
    path = make_fake_gtfs_zip(bad_csv)
    with pytest.raises(ValueError, match="Missing column"):
        parse_stops(path, "stockholm")
