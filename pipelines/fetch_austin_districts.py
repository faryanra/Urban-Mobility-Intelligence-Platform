"""Fetch Austin council district boundaries from City of Austin open data."""
import json
from pathlib import Path

import requests

OUT = Path("pipelines/data/raw/austin_council_districts.geojson")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Austin single-member council districts via ArcGIS REST
URL = (
    "https://services.arcgis.com/0L95CJ0VTaxqcmED/arcgis/rest/services"
    "/BOUNDARIES_single_member_districts/FeatureServer/0/query"
    "?where=1%3D1&outFields=*&outSR=4326&f=geojson"
)
r = requests.get(URL, timeout=60)
r.raise_for_status()
OUT.write_bytes(r.content)
data = json.loads(r.content)
print(f"Downloaded {len(data['features'])} council districts")
