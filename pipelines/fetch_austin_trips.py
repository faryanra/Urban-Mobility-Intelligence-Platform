"""Download the first 50,000 Austin shared micromobility trips from the city's Socrata API."""

from pathlib import Path

import requests

RAW = Path("pipelines/data/raw")
DEST = RAW / "austin_trips.csv"
AUSTIN_SAMPLE = 50_000  # the full dataset is ~1 GB


def download_austin() -> Path:
    if DEST.exists():
        print(f"  already exists: {DEST.name}")
        return DEST
    RAW.mkdir(parents=True, exist_ok=True)
    url = (
        "https://data.austintexas.gov/resource/7d8e-dm7r.csv"
        f"?$limit={AUSTIN_SAMPLE}&$order=:id"
    )
    print(f"  downloading {DEST.name} ...")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with open(DEST, "wb") as f:
        f.writelines(response.iter_content(1024 * 1024))
    print(f"  saved {DEST}")
    return DEST


if __name__ == "__main__":
    download_austin()
