"""Download OSM walk graphs for EU cities and cache as GraphML."""

import os

import osmnx as ox

CITIES = {
    "stockholm": "Stockholm, Sweden",
    "amsterdam": "Amsterdam, Netherlands",
}
CACHE_DIR = "api/data/osm_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

for city, place in CITIES.items():
    out_path = f"{CACHE_DIR}/{city}_walk.graphml"
    if os.path.exists(out_path):
        print(f"  {city}: cache exists, skipping")
        continue
    print(f"  Downloading {city} OSM walk graph...")
    G = ox.graph_from_place(place, network_type="walk", simplify=True)
    ox.save_graphml(G, out_path)
    nodes, edges = ox.graph_to_gdfs(G)
    print(f"  {city}: {len(nodes)} nodes, {len(edges)} edges → {out_path}")

print("Done.")
