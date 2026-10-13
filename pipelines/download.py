"""Download raw datasets from public sources."""

import zipfile
from pathlib import Path

import requests

RAW = Path("pipelines/data/raw")
RAW.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, chunk_size: int = 1024 * 1024) -> None:
    if dest.exists():
        print(f"  already exists: {dest.name}")
        return
    print(f"  downloading {dest.name} ...")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    with open(dest, "wb") as f:
        f.writelines(response.iter_content(chunk_size))
    print(f"  done: {dest}")


AUSTIN_SAMPLE = 50_000  # rows; full dataset is ~1 GB, sample fits on constrained disks


def download_austin() -> Path:
    url = (
        "https://data.austintexas.gov/resource/7d8e-dm7r.csv"
        f"?$limit={AUSTIN_SAMPLE}&$order=:id"
    )
    dest = RAW / "austin_trips.csv"
    download_file(url, dest)
    return dest


def download_chicago() -> Path:
    zip_dest = RAW / "divvy_2013_jun.zip"
    csv_dest = RAW / "chicago_divvy_2013_jun.csv"

    if not csv_dest.exists():
        download_file(
            "https://divvy-tripdata.s3.amazonaws.com/Divvy_Stations_Trips_2013.zip",
            zip_dest,
        )
        with zipfile.ZipFile(zip_dest, "r") as z:
            for name in z.namelist():
                basename = name.split("/")[-1]
                if basename.endswith(".csv") and "Trips" in basename:
                    z.extract(name, RAW)
                    extracted = RAW / name
                    extracted.rename(csv_dest)
                    break
        zip_dest.unlink(missing_ok=True)

    return csv_dest


if __name__ == "__main__":
    print("Austin:")
    download_austin()
    print("Chicago:")
    download_chicago()
    print("Done.")
