-- WLC accessibility grid (square cells built in the city's metric CRS, stored in WGS84)
CREATE TABLE IF NOT EXISTS accessibility_cells (
    id            BIGSERIAL PRIMARY KEY,
    city          VARCHAR(50) NOT NULL,
    transit_score DOUBLE PRECISION NOT NULL,
    density_score DOUBLE PRECISION NOT NULL,
    accessibility DOUBLE PRECISION NOT NULL,
    nearest_stop_m DOUBLE PRECISION NOT NULL,
    geom          geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accessibility_cells_city
    ON accessibility_cells (city);
CREATE INDEX IF NOT EXISTS idx_accessibility_cells_geom
    ON accessibility_cells USING GIST (geom);
