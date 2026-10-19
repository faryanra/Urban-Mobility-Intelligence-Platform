"""FastAPI endpoint tests against a migrated (possibly empty) PostGIS database."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_openapi_schema(client):
    routes = client.get("/openapi.json").json()["paths"]
    for path in ("/api/accessibility", "/api/catchment", "/api/trips/breakdown"):
        assert path in routes
    assert "/api/stops" not in routes


def test_unknown_city_rejected(client):
    assert client.get("/api/accessibility?city=berlin").status_code == 422
    assert client.get("/api/accessibility/stats?city=../etc").status_code == 422
    assert client.get("/api/tiles/stops/0/0/0.mvt?city=berlin").status_code == 422


def test_accessibility_is_feature_collection(client):
    resp = client.get("/api/accessibility?city=amsterdam")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)


def test_stops_tile(client):
    resp = client.get("/api/tiles/stops/10/550/300.mvt?city=stockholm")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/x-protobuf"


def test_trips_breakdown_shape(client):
    data = client.get("/api/trips/breakdown").json()
    assert data["timezone"] == "America/Chicago"
    assert set(data["period"]) == {"start", "end"}
    assert isinstance(data["by_hour"], list)


def test_od_endpoints(client):
    for path in ("/api/od/chicago", "/api/od/austin"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_chicago_summary_and_stations(client):
    summary = client.get("/api/trips/summary/chicago").json()
    assert {"trip_count", "median_duration_min", "active_stations", "period_start"} <= set(summary)
    stations = client.get("/api/stations/chicago").json()
    assert stations["type"] == "FeatureCollection"
    for feature in stations["features"]:
        assert feature["geometry"]["type"] == "Point"
        assert "departures" in feature["properties"]


def test_geometry_is_object_not_string(client):
    for path in ("/api/districts/austin", "/api/districts/chicago", "/api/metro/chicago"):
        for feature in client.get(path).json()["features"]:
            assert isinstance(feature["geometry"], dict)


def test_catchment_unavailable_without_graph(client, monkeypatch):
    import api.main
    monkeypatch.setitem(api.main._graphs, "amsterdam", None)
    resp = client.get("/api/catchment?lat=52.37&lng=4.90&city=amsterdam")
    assert resp.status_code == 503


def test_catchment_validates_input(client):
    resp = client.get("/api/catchment?lat=999&lng=18.07&city=stockholm")
    assert resp.status_code == 422
