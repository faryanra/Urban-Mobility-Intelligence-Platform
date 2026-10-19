"""Fetch Chicago ward boundaries and CTA L train lines."""
import json
from pathlib import Path

import requests

Path("pipelines/data/raw").mkdir(parents=True, exist_ok=True)

downloads = {
    "chicago_wards.geojson": "https://data.cityofchicago.org/resource/p293-wvbd.geojson?$limit=1000",
    "chicago_cta_lines.geojson": "https://data.cityofchicago.org/resource/xbyr-jnvx.geojson?$limit=1000",
}

for filename, url in downloads.items():
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path = Path("pipelines/data/raw") / filename
    path.write_bytes(r.content)
    data = json.loads(r.content)
    print(f"{filename}: {len(data['features'])} features")
