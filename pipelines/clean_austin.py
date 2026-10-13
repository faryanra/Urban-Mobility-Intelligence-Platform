"""Clean and normalize Austin micromobility trips."""

from pathlib import Path

import pandas as pd

RAW = Path("pipelines/data/raw/austin_trips.csv")
OUT = Path("pipelines/data/processed/austin_clean.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Socrata API returns snake_case; legacy web CSV uses verbose names — handle both
RENAME_LEGACY = {
    "ID": "trip_id",
    "Device ID": "device_id",
    "Vehicle Type": "vehicle_type",
    "Trip Duration": "trip_duration",
    "Trip Distance": "trip_distance",
    "Start Time": "start_time",
    "End Time": "end_time",
    "Census Tract Start": "census_geoid_start",
    "Census Tract End": "census_geoid_end",
}

KEEP_COLS = [
    "trip_id", "device_id", "vehicle_type", "trip_duration", "trip_distance",
    "start_time", "end_time", "census_geoid_start", "census_geoid_end",
    "council_district_start", "council_district_end", "year", "month",
]


def clean() -> pd.DataFrame:
    df = pd.read_csv(RAW, low_memory=False)

    # Normalise legacy verbose column names if present
    df = df.rename(columns={k: v for k, v in RENAME_LEGACY.items() if k in df.columns})

    # Preserve coordinate columns before column filter
    lat_candidates = [c for c in df.columns if "lat" in c.lower() and c not in KEEP_COLS]
    lon_candidates = [c for c in df.columns if "lon" in c.lower() and c not in KEEP_COLS]
    if lat_candidates:
        df = df.rename(columns={lat_candidates[0]: "origin_lat"})
    if lon_candidates:
        df = df.rename(columns={lon_candidates[0]: "origin_lon"})

    # Keep only columns that exist (plus coords if present)
    coord_cols = [c for c in ["origin_lat", "origin_lon"] if c in df.columns]
    df = df[[c for c in KEEP_COLS if c in df.columns] + coord_cols]

    # Parse times
    for col in ["start_time", "end_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Remove nulls in critical fields
    df = df.dropna(subset=["trip_id", "start_time"])

    # Remove unrealistic durations (< 60s or > 24h)
    if "trip_duration" in df.columns:
        df = df[df["trip_duration"].between(60, 86400)]

    df["city"] = "austin"
    df = df.reset_index(drop=True)

    print(f"Austin: {len(df):,} trips after cleaning")
    return df


if __name__ == "__main__":
    df = clean()
    df.to_parquet(OUT, index=False)
    print(f"Saved: {OUT}")
    print(df.dtypes)
    print(df.head(3))
