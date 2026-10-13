"""Tests for data validation schemas."""

import pytest
from pipelines.schemas import AustinTrip, ChicagoTrip
from pydantic import ValidationError


def test_austin_valid():
    trip = AustinTrip(
        trip_id="ABC123",
        vehicle_type="scooter",
        trip_duration=300,
        origin_lat=30.27,
        origin_lon=-97.74,
        dest_lat=30.28,
        dest_lon=-97.73,
    )
    assert trip.city == "austin"
    assert trip.origin_lat == 30.27


def test_austin_invalid_lat():
    with pytest.raises(ValidationError):
        AustinTrip(origin_lat=999)


def test_chicago_valid():
    trip = ChicagoTrip(
        trip_id="1",
        from_station_id="35",
        to_station_id="42",
        from_lat=41.88,
        from_lon=-87.63,
        to_lat=41.89,
        to_lon=-87.64,
    )
    assert trip.city == "chicago"
    assert trip.vehicle_type == "bike"


def test_chicago_invalid_lon():
    with pytest.raises(ValidationError):
        ChicagoTrip(from_lon=200)
