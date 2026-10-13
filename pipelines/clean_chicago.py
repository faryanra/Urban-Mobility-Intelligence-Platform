"""Clean and normalize Chicago Divvy trips."""

from pathlib import Path

import pandas as pd

RAW = Path("pipelines/data/raw/chicago_divvy_2013_jun.csv")
OUT = Path("pipelines/data/processed/chicago_clean.parquet")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Handle both legacy verbose headers and the 2013 snake_case CSV format
RENAME = {
    # Legacy verbose (older exports)
    "TRIP DURATION": "trip_duration",
    "FROM STATION ID": "from_station_id",
    "TO STATION ID": "to_station_id",
    "START TIME": "start_time",
    "STOP TIME": "stop_time",
    "FROM LATITUDE": "origin_lat",
    "FROM LONGITUDE": "origin_lon",
    "TO LATITUDE": "dest_lat",
    "TO LONGITUDE": "dest_lon",
    "BIKEID": "bike_id",
    "USERTYPE": "user_type",
    # 2013 CSV format
    "tripduration": "trip_duration",
    "starttime": "start_time",
    "stoptime": "stop_time",
    "bikeid": "bike_id",
    "usertype": "user_type",
}


def clean() -> pd.DataFrame:
    df = pd.read_csv(RAW, low_memory=False)

    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})

    for col in ["start_time", "stop_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df = df.dropna(subset=["from_station_id", "to_station_id", "start_time"])

    if "trip_duration" in df.columns:
        df = df[df["trip_duration"].between(60, 86400)]

    # Validate coordinates if present (not all exports include them)
    for lat_col, lon_col in [("origin_lat", "origin_lon"), ("dest_lat", "dest_lon")]:
        if lat_col in df.columns:
            df = df[df[lat_col].between(-90, 90) & df[lon_col].between(-180, 180)]

    df["city"] = "chicago"
    df["vehicle_type"] = "bike"
    df = df.reset_index(drop=True)

    print(f"Chicago: {len(df):,} trips after cleaning")
    return df


if __name__ == "__main__":
    df = clean()
    df.to_parquet(OUT, index=False)
    print(f"Saved: {OUT}")
    print(df.dtypes)
    print(df.head(3))
