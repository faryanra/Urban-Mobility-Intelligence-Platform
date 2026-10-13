"""Fetch OSMnx road networks for Stockholm and Amsterdam, save as GeoPackage."""

from pathlib import Path

import osmnx as ox

OUT_DIR = Path("pipelines/data/networks")

CITIES = {
    "stockholm": {
        "query": "Stockholm, Sweden",
        "crs": "EPSG:3006",
    },
    "amsterdam": {
        "query": "Amsterdam, Netherlands",
        "crs": "EPSG:28992",
    },
}


def build_network(city: str, config: dict) -> None:
    print(f"Fetching road network: {config['query']}...")
    G = ox.graph_from_place(config["query"], network_type="drive")

    nodes, edges = ox.graph_to_gdfs(G)

    nodes_proj = nodes.to_crs(config["crs"])
    edges_proj = edges.to_crs(config["crs"])

    out_path = OUT_DIR / f"{city}_network.gpkg"
    nodes_proj.to_file(out_path, layer="nodes", driver="GPKG")
    edges_proj.to_file(out_path, layer="edges", driver="GPKG")

    print(f"  {len(nodes):,} nodes, {len(edges):,} edges → {out_path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for city, config in CITIES.items():
        build_network(city, config)
    print("Networks complete.")


if __name__ == "__main__":
    main()
