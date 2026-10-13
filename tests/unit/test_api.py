"""FastAPI endpoint tests."""

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
    assert "status" in resp.json()


def test_openapi_schema(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    routes = list(schema["paths"].keys())
    assert "/api/trips/summary" in routes
    assert "/api/stops" in routes
    assert "/api/accessibility" in routes
    assert "/api/catchment" in routes


def test_stops_bad_city(client):
    resp = client.get("/api/stops?city=berlin")
    assert resp.status_code == 400


def test_accessibility_missing_city(client):
    resp = client.get("/api/accessibility?city=nowhere")
    assert resp.status_code == 404


def test_trips_summary(client):
    resp = client.get("/api/trips/summary")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_od_chicago(client):
    resp = client.get("/api/od/chicago")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_od_austin(client):
    resp = client.get("/api/od/austin")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_catchment_no_graph(client):
    """Returns empty FeatureCollection when OSM graph absent (CI has no cache)."""
    resp = client.get("/api/catchment?lat=59.33&lng=18.07&city=stockholm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
