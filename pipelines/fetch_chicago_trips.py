"""Fetch a 50,000-trip Divvy sample (summer 2013) from the Chicago open data portal."""
from pathlib import Path

import pandas as pd
import requests

OUT = Path("pipelines/data/raw/chicago_divvy_trips_june2013.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

# First, probe columns with a small request
probe = requests.get(
    "https://data.cityofchicago.org/resource/fg6s-gzvg.json?$limit=5",
    timeout=60,
)
probe.raise_for_status()
sample = probe.json()
if sample:
    print("Columns:", list(sample[0].keys()))

# Determine start time column name
start_col = None
if sample:
    for candidate in ("starttime", "start_time", "trip_start", "started_at"):
        if candidate in sample[0]:
            start_col = candidate
            break

if start_col:
    URL = (
        f"https://data.cityofchicago.org/resource/fg6s-gzvg.json"
        f"?$limit=50000"
        f"&$where={start_col} >= '2013-06-01T00:00:00' AND {start_col} <= '2013-06-30T23:59:59'"
    )
else:
    print("Could not detect start time column — fetching without date filter")
    URL = "https://data.cityofchicago.org/resource/fg6s-gzvg.json?$limit=50000"

r = requests.get(URL, timeout=120)
r.raise_for_status()
data = r.json()
print(f"Downloaded {len(data)} trips")

df = pd.DataFrame(data)
print("Columns:", df.columns.tolist())
df.to_csv(OUT, index=False)
print(f"Saved to {OUT}")
