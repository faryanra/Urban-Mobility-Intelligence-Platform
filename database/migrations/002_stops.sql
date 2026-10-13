CREATE TABLE IF NOT EXISTS transit_stops (
    id        BIGSERIAL PRIMARY KEY,
    stop_id   TEXT NOT NULL,
    stop_name TEXT,
    city      VARCHAR(50),
    geom      geometry(Point, 4326),
    UNIQUE(stop_id, city)
);
CREATE INDEX IF NOT EXISTS idx_transit_stops_geom ON transit_stops USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_transit_stops_city ON transit_stops (city);
