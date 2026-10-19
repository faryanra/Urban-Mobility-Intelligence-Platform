ALTER TABLE chicago_trips
    ADD COLUMN IF NOT EXISTS from_station_name TEXT,
    ADD COLUMN IF NOT EXISTS to_station_name   TEXT;
