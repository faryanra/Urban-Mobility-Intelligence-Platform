"""Download WorldPop population raster for Europe."""

from pathlib import Path

import requests

RAW = Path("spatial/data/raw")
RAW.mkdir(parents=True, exist_ok=True)


def fetch_worldpop_sweden() -> Path:
    """Download Sweden 100m population raster from WorldPop."""
    dest = RAW / "worldpop_swe_2020.tif"
    if dest.exists():
        print(f"  skip: {dest.name}")
        return dest
    url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/SWE/swe_ppp_2020.tif"
    print(f"  downloading {dest.name} ...")
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.writelines(r.iter_content(1024 * 1024))
    size_mb = dest.stat().st_size // (1024 * 1024)
    print(f"  saved {size_mb} MB")
    return dest


def fetch_worldpop_netherlands() -> Path:
    """Download Netherlands 100m population raster from WorldPop."""
    dest = RAW / "worldpop_nld_2020.tif"
    if dest.exists():
        print(f"  skip: {dest.name}")
        return dest
    url = "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/NLD/nld_ppp_2020.tif"
    print(f"  downloading {dest.name} ...")
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.writelines(r.iter_content(1024 * 1024))
    size_mb = dest.stat().st_size // (1024 * 1024)
    print(f"  saved {size_mb} MB")
    return dest


if __name__ == "__main__":
    print("Sweden (Stockholm):")
    fetch_worldpop_sweden()
    print("Netherlands (Amsterdam):")
    fetch_worldpop_netherlands()
