"""Download GTFS feeds for Stockholm (SL) and Amsterdam (GVB)."""

from pathlib import Path

import requests

RAW = Path("pipelines/data/raw")
RAW.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path, headers: dict | None = None) -> None:
    if dest.exists():
        print(f"  skip: {dest.name}")
        return
    print(f"  downloading {dest.name} ...")
    r = requests.get(url, headers=headers or {}, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.writelines(r.iter_content(1024 * 512))
    print(f"  saved {dest.stat().st_size // 1024} KB")


def fetch_stockholm(api_key: str) -> Path:
    dest = RAW / "sl_gtfs.zip"
    url = f"https://opendata.samtrafiken.se/gtfs/sl/sl.zip?key={api_key}"
    download(url, dest)
    return dest


def fetch_amsterdam() -> Path:
    dest = RAW / "gvb_gtfs.zip"
    # OVapi merged per-operator feeds into a national feed; GVB is included
    url = "https://gtfs.ovapi.nl/nl/gtfs-nl.zip"
    download(url, dest)
    return dest


if __name__ == "__main__":
    import sys
    api_key = sys.argv[1] if len(sys.argv) > 1 else ""
    if api_key:
        print("Stockholm SL:")
        fetch_stockholm(api_key)
    else:
        print("  skip Stockholm — no API key provided")
    print("Amsterdam GVB:")
    fetch_amsterdam()
