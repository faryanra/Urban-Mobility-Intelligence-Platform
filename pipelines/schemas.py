"""Pydantic schemas for raw data validation."""


from pydantic import BaseModel, field_validator


class AustinTrip(BaseModel):
    trip_id: str | None = None
    device_id: str | None = None
    vehicle_type: str | None = None
    trip_duration: float | None = None
    trip_distance: float | None = None
    start_time: str | None = None
    end_time: str | None = None
    origin_lat: float | None = None
    origin_lon: float | None = None
    dest_lat: float | None = None
    dest_lon: float | None = None
    city: str = "austin"

    @field_validator("origin_lat", "dest_lat", mode="before")
    @classmethod
    def lat_range(cls, v):
        if v is not None and not (-90 <= float(v) <= 90):
            raise ValueError(f"Invalid latitude: {v}")
        return v

    @field_validator("origin_lon", "dest_lon", mode="before")
    @classmethod
    def lon_range(cls, v):
        if v is not None and not (-180 <= float(v) <= 180):
            raise ValueError(f"Invalid longitude: {v}")
        return v


class ChicagoTrip(BaseModel):
    trip_id: str | None = None
    duration_sec: int | None = None
    from_station_id: str | None = None
    to_station_id: str | None = None
    start_time: str | None = None
    stop_time: str | None = None
    from_lat: float | None = None
    from_lon: float | None = None
    to_lat: float | None = None
    to_lon: float | None = None
    city: str = "chicago"
    vehicle_type: str = "bike"

    @field_validator("from_lat", "to_lat", mode="before")
    @classmethod
    def lat_range(cls, v):
        if v is not None and not (-90 <= float(v) <= 90):
            raise ValueError(f"Invalid latitude: {v}")
        return v

    @field_validator("from_lon", "to_lon", mode="before")
    @classmethod
    def lon_range(cls, v):
        if v is not None and not (-180 <= float(v) <= 180):
            raise ValueError(f"Invalid longitude: {v}")
        return v
