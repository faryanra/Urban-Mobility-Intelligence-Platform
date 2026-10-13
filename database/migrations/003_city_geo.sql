-- Austin council districts with trip aggregates
CREATE TABLE IF NOT EXISTS austin_districts (
    id          BIGSERIAL PRIMARY KEY,
    district_id TEXT NOT NULL UNIQUE,
    district_name TEXT,
    geom        geometry(MultiPolygon, 4326),
    centroid    geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_austin_districts_geom
    ON austin_districts USING GIST (geom);

-- Chicago wards
CREATE TABLE IF NOT EXISTS chicago_wards (
    id       BIGSERIAL PRIMARY KEY,
    ward_id  TEXT NOT NULL UNIQUE,
    geom     geometry(MultiPolygon, 4326),
    centroid geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_chicago_wards_geom
    ON chicago_wards USING GIST (geom);

-- Chicago CTA L lines
CREATE TABLE IF NOT EXISTS chicago_metro_lines (
    id        BIGSERIAL PRIMARY KEY,
    line_name TEXT,
    color     TEXT,
    geom      geometry(MultiLineString, 4326)
);
CREATE INDEX IF NOT EXISTS idx_chicago_metro_geom
    ON chicago_metro_lines USING GIST (geom);

-- Chicago Divvy trips (June 2013 sample)
CREATE TABLE IF NOT EXISTS chicago_trips (
    id              BIGSERIAL PRIMARY KEY,
    trip_id         TEXT,
    from_station_id TEXT,
    to_station_id   TEXT,
    from_lat        DOUBLE PRECISION,
    from_lng        DOUBLE PRECISION,
    to_lat          DOUBLE PRECISION,
    to_lng          DOUBLE PRECISION,
    duration_sec    INTEGER,
    start_time      TIMESTAMP,
    user_type       TEXT
);
