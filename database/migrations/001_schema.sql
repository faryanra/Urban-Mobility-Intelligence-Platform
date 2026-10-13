CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    country VARCHAR(50) NOT NULL,
    center_geom geometry(Point, 4326)
);

INSERT INTO cities (name, country, center_geom) VALUES
  ('austin',    'USA',         ST_SetSRID(ST_MakePoint(-97.7431, 30.2672), 4326)),
  ('chicago',   'USA',         ST_SetSRID(ST_MakePoint(-87.6298, 41.8781), 4326)),
  ('stockholm', 'Sweden',      ST_SetSRID(ST_MakePoint(18.0686, 59.3293), 4326)),
  ('amsterdam', 'Netherlands', ST_SetSRID(ST_MakePoint(4.9041, 52.3676), 4326))
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS stations (
    id SERIAL PRIMARY KEY,
    station_id TEXT NOT NULL,
    name TEXT,
    city VARCHAR(50) NOT NULL,
    geom geometry(Point, 4326),
    UNIQUE(station_id, city)
);

CREATE TABLE IF NOT EXISTS mobility_trips (
    id BIGSERIAL PRIMARY KEY,
    trip_id TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_sec INT,
    vehicle_type VARCHAR(20),
    origin_geom geometry(Point, 4326),
    dest_geom geometry(Point, 4326),
    from_station_id TEXT,
    to_station_id TEXT,
    city VARCHAR(50) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trips_origin ON mobility_trips USING GIST (origin_geom);
CREATE INDEX IF NOT EXISTS idx_trips_dest   ON mobility_trips USING GIST (dest_geom);
CREATE INDEX IF NOT EXISTS idx_trips_city   ON mobility_trips (city);
CREATE INDEX IF NOT EXISTS idx_trips_time   ON mobility_trips (start_time);
