"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { BASE, City, CityData, FlowRow, fetchCatchment, isEuCity } from "../../lib/api";

if (typeof window !== "undefined") {
  setWorkerUrl("/maplibre-gl-worker.mjs");
}

const BASEMAP = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const CITY_VIEW: Record<City, { center: [number, number]; zoom: number }> = {
  stockholm: { center: [18.07, 59.33], zoom: 11 },
  amsterdam: { center: [4.90, 52.37], zoom: 12 },
  austin:    { center: [-97.75, 30.29], zoom: 10.3 },
  chicago:   { center: [-87.64, 41.885], zoom: 12 },
};

// Bottom-to-top draw order of every layer this component owns.
const LAYER_ORDER = [
  "accessibility-fill", "accessibility-outline",
  "districts-fill", "districts-outline",
  "wards-fill", "wards-outline",
  "chicago-metro-lines",
  "catchment-lines",
  "stops-hitarea", "stops-layer",
  "chicago-stations",
  "austin-od-arcs", "chicago-od-arcs",
  "district-label-text",
];
const SOURCES = [
  "accessibility", "stops-mvt", "catchment", "districts", "district-labels",
  "austin-od", "wards", "metro", "stations", "od-arcs",
];

const EMPTY_FC: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

const esc = (v: unknown) =>
  String(v ?? "").replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string
  ));

function popupHTML(title: string, rows: [string, unknown][]) {
  return `<div class="popup-content"><div class="popup-title">${esc(title)}</div>${rows
    .map(([k, v]) => `<div class="popup-row"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`)
    .join("")}</div>`;
}

function buildArcs(flows: FlowRow[]): GeoJSON.FeatureCollection {
  if (!flows.length) return EMPTY_FC;
  const maxFlow = Math.max(...flows.map(f => Number(f.flow_count)));
  return {
    type: "FeatureCollection",
    features: flows.map(f => {
      const fx = Number(f.from_lng), fy = Number(f.from_lat);
      const tx = Number(f.to_lng), ty = Number(f.to_lat);
      const dx = tx - fx, dy = ty - fy;
      const len = Math.sqrt(dx * dx + dy * dy) || 1;
      const offset = Math.min(len * 0.4, 0.05);
      const cx = (fx + tx) / 2 - (dy / len) * offset;
      const cy = (fy + ty) / 2 + (dx / len) * offset;
      const coords: [number, number][] = [];
      for (let i = 0; i <= 20; i++) {
        const t = i / 20;
        coords.push([
          (1 - t) * (1 - t) * fx + 2 * (1 - t) * t * cx + t * t * tx,
          (1 - t) * (1 - t) * fy + 2 * (1 - t) * t * cy + t * t * ty,
        ]);
      }
      return {
        type: "Feature",
        geometry: { type: "LineString", coordinates: coords },
        properties: {
          flow_count: Number(f.flow_count),
          weight: maxFlow > 0 ? Number(f.flow_count) / maxFlow : 0,
          from: f.from_station_name ?? f.from_district ?? "",
          to: f.to_station_name ?? f.to_district ?? "",
        },
      };
    }),
  };
}

function clearOwnLayers(map: maplibregl.Map) {
  for (const id of [...LAYER_ORDER].reverse()) if (map.getLayer(id)) map.removeLayer(id);
  for (const id of SOURCES) if (map.getSource(id)) map.removeSource(id);
}

function addLayer(map: maplibregl.Map, layer: maplibregl.LayerSpecification) {
  const idx = LAYER_ORDER.indexOf(layer.id);
  const before = LAYER_ORDER.slice(idx + 1).find(id => map.getLayer(id));
  map.addLayer(layer, before);
}

function addGeoJSON(map: maplibregl.Map, id: string, data: GeoJSON.GeoJSON) {
  map.addSource(id, { type: "geojson", data });
}

function drawEU(map: maplibregl.Map, city: City, accessibility: GeoJSON.FeatureCollection) {
  addGeoJSON(map, "accessibility", accessibility);
  addLayer(map, {
    id: "accessibility-fill", type: "fill", source: "accessibility",
    paint: {
      "fill-color": [
        "interpolate", ["linear"], ["get", "accessibility"],
        0.0, "#1e3a5f", 0.3, "#0d6e6e", 0.6, "#0d9488", 0.8, "#a3e635", 1.0, "#fde68a",
      ],
      "fill-opacity": 0.65,
    },
  });
  addLayer(map, {
    id: "accessibility-outline", type: "line", source: "accessibility",
    paint: { "line-color": "#0d9488", "line-width": 0.3, "line-opacity": 0.3 },
  });

  map.addSource("stops-mvt", {
    type: "vector",
    tiles: [`${BASE}/api/tiles/stops/{z}/{x}/{y}.mvt?city=${city}`],
    minzoom: 0, maxzoom: 16,
  });
  addLayer(map, {
    id: "stops-hitarea", type: "circle", source: "stops-mvt", "source-layer": "stops",
    paint: { "circle-radius": 10, "circle-opacity": 0, "circle-color": "#000" },
  });
  addLayer(map, {
    id: "stops-layer", type: "circle", source: "stops-mvt", "source-layer": "stops",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 14, 5],
      "circle-color": "#4ECDC4",
      "circle-opacity": 0.75,
      "circle-stroke-width": 0.5,
      "circle-stroke-color": "#ffffff",
    },
  });
}

function drawAustin(map: maplibregl.Map, districts: GeoJSON.FeatureCollection, od: FlowRow[]) {
  addGeoJSON(map, "districts", districts);
  addLayer(map, {
    id: "districts-fill", type: "fill", source: "districts",
    paint: { "fill-color": "#F59E0B", "fill-opacity": 0.05 },
  });
  addLayer(map, {
    id: "districts-outline", type: "line", source: "districts",
    paint: { "line-color": "#F59E0B", "line-width": 1.5, "line-opacity": 0.7 },
  });

  const labels = districts.features.flatMap(f => {
    const c = f.properties?.centroid as GeoJSON.Point | undefined;
    return c?.type === "Point"
      ? [{ type: "Feature" as const, geometry: c, properties: { district_id: f.properties?.district_id } }]
      : [];
  });
  addGeoJSON(map, "district-labels", { type: "FeatureCollection", features: labels });
  addLayer(map, {
    id: "district-label-text", type: "symbol", source: "district-labels",
    layout: {
      "text-field": ["get", "district_id"],
      "text-size": 12,
      "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
    },
    paint: { "text-color": "#F59E0B", "text-halo-color": "#0f172a", "text-halo-width": 1.5 },
  });

  addGeoJSON(map, "austin-od", buildArcs(od));
  addLayer(map, {
    id: "austin-od-arcs", type: "line", source: "austin-od",
    paint: {
      "line-color": "#F59E0B",
      "line-opacity": ["interpolate", ["linear"], ["get", "weight"], 0, 0.2, 1, 0.85],
      "line-width": ["interpolate", ["linear"], ["get", "weight"], 0, 0.5, 1, 3.5],
    },
  });
}

function drawChicago(
  map: maplibregl.Map,
  wards: GeoJSON.FeatureCollection,
  metro: GeoJSON.FeatureCollection,
  stations: GeoJSON.FeatureCollection,
  od: FlowRow[],
) {
  addGeoJSON(map, "wards", wards);
  addLayer(map, {
    id: "wards-fill", type: "fill", source: "wards",
    paint: { "fill-color": "#1e293b", "fill-opacity": 0.4 },
  });
  addLayer(map, {
    id: "wards-outline", type: "line", source: "wards",
    paint: { "line-color": "#334155", "line-width": 0.8 },
  });
  addGeoJSON(map, "metro", metro);
  addLayer(map, {
    id: "chicago-metro-lines", type: "line", source: "metro",
    layout: { "line-join": "round", "line-cap": "round" },
    paint: { "line-color": "#EF4444", "line-width": 2.5, "line-opacity": 0.9 },
  });
  addGeoJSON(map, "stations", stations);
  addLayer(map, {
    id: "chicago-stations", type: "circle", source: "stations",
    paint: {
      "circle-radius": 4,
      "circle-color": "#4ECDC4",
      "circle-opacity": 0.8,
      "circle-stroke-width": 0.5,
      "circle-stroke-color": "#ffffff",
    },
  });
  addGeoJSON(map, "od-arcs", buildArcs(od));
  addLayer(map, {
    id: "chicago-od-arcs", type: "line", source: "od-arcs",
    paint: {
      "line-color": "#F59E0B",
      "line-opacity": ["interpolate", ["linear"], ["get", "weight"], 0, 0.2, 1, 0.9],
      "line-width": ["interpolate", ["linear"], ["get", "weight"], 0, 0.5, 1, 4],
    },
  });
}

interface MapViewProps {
  city: City;
  data: CityData | null;
  wlcThreshold: number;
}

export default function MapView({ city, data, wlcThreshold }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const cityRef = useRef(city);
  const catchmentAbort = useRef<AbortController | null>(null);
  const [styleReady, setStyleReady] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  cityRef.current = city;

  // Create the map once; tooltip and click handlers are delegated by layer id.
  useEffect(() => {
    if (!containerRef.current) return;
    setStyleReady(false);
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP,
      center: CITY_VIEW[cityRef.current].center,
      zoom: CITY_VIEW[cityRef.current].zoom,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    const popup = new maplibregl.Popup({
      closeButton: false, closeOnClick: false, className: "mobility-popup",
    });
    const hover = (layer: string, html: (p: Record<string, unknown>) => string, cursor = "pointer") => {
      map.on("mousemove", layer, e => {
        const props = e.features?.[0]?.properties;
        if (!props) return;
        popup.setLngLat(e.lngLat).setHTML(html(props)).addTo(map);
        map.getCanvas().style.cursor = cursor;
      });
      map.on("mouseleave", layer, () => {
        popup.remove();
        map.getCanvas().style.cursor = "";
      });
    };

    hover("accessibility-fill", p => popupHTML("Grid cell (500 m)", [
      ["WLC score", Number(p.accessibility).toFixed(3)],
      ["Transit (70%)", Number(p.transit_score).toFixed(3)],
      ["Population (30%)", Number(p.density_score).toFixed(3)],
      ["Nearest stop", `${Math.round(Number(p.nearest_stop_m))} m`],
    ]), "crosshair");
    hover("stops-layer", p => popupHTML(String(p.stop_name || "Transit stop"), [
      ["Stop ID", p.stop_id],
      ["Action", "Click for walking catchment"],
    ]));
    hover("districts-fill", p => popupHTML(`District ${p.district_id}`, [
      ["Trips starting here", Number(p.trip_count).toLocaleString()],
    ]), "");
    hover("austin-od-arcs", p => popupHTML("District flow", [
      ["From district", p.from], ["To district", p.to],
      ["Trips", Number(p.flow_count).toLocaleString()],
    ]));
    hover("chicago-stations", p => popupHTML(String(p.name || "Divvy station"), [
      ["Station ID", p.id],
      ["Trips started", Number(p.departures).toLocaleString()],
    ]));
    hover("chicago-od-arcs", p => popupHTML("Trip corridor", [
      ["From station", p.from], ["To station", p.to],
      ["Trips", Number(p.flow_count).toLocaleString()],
    ]));

    map.on("click", "stops-hitarea", async e => {
      const current = cityRef.current;
      const point = e.features?.[0]?.geometry;
      if (!isEuCity(current) || point?.type !== "Point") return;
      const [lng, lat] = point.coordinates;

      catchmentAbort.current?.abort();
      const controller = new AbortController();
      catchmentAbort.current = controller;
      setNotice("Computing 500 m walking catchment...");
      try {
        const fc = await fetchCatchment(current, lat, lng, controller.signal);
        if (controller.signal.aborted || cityRef.current !== current) return;
        const src = map.getSource("catchment") as maplibregl.GeoJSONSource | undefined;
        if (src) {
          src.setData(fc);
        } else {
          addGeoJSON(map, "catchment", fc);
          addLayer(map, {
            id: "catchment-lines", type: "line", source: "catchment",
            paint: { "line-color": "#F59E0B", "line-width": 2, "line-opacity": 0.85 },
          });
        }
        setNotice(null);
      } catch (err) {
        if ((err as Error).name !== "AbortError") setNotice((err as Error).message);
      }
    });
    map.on("mouseenter", "stops-hitarea", () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "stops-hitarea", () => { map.getCanvas().style.cursor = ""; });

    map.on("load", () => setStyleReady(true));

    return () => {
      catchmentAbort.current?.abort();
      popup.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Swap layers when the city or its data changes; the map itself is reused.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady) return;
    catchmentAbort.current?.abort();
    setNotice(null);
    clearOwnLayers(map);
    if (!data) return;
    if (data.kind === "eu") drawEU(map, city, data.accessibility);
    if (data.kind === "austin") drawAustin(map, data.districts, data.od);
    if (data.kind === "chicago") drawChicago(map, data.wards, data.metro, data.stations, data.od);
  }, [styleReady, city, data]);

  useEffect(() => {
    mapRef.current?.jumpTo(CITY_VIEW[city]);
  }, [city]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleReady || !map.getLayer("accessibility-fill")) return;
    const filter = wlcThreshold > 0
      ? (["<", ["get", "accessibility"], wlcThreshold] as maplibregl.FilterSpecification)
      : null;
    map.setFilter("accessibility-fill", filter);
    map.setFilter("accessibility-outline", filter);
  }, [wlcThreshold, styleReady, data]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {!styleReady && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900 text-slate-400 text-sm pointer-events-none">
          Loading map...
        </div>
      )}
      {notice && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 z-20 max-w-[80%] bg-slate-900/95 text-slate-200 text-xs px-3 py-2 rounded-md border border-slate-700">
          {notice}
        </div>
      )}
      {isEuCity(city) && data?.kind === "eu" && (
        <div className="map-legend">
          <div className="legend-title">WLC accessibility score</div>
          <div className="legend-gradient" />
          <div className="legend-labels">
            <span>0.0 low</span><span>0.5</span><span>1.0 high</span>
          </div>
          <div className="legend-note">Transit proximity 70% + population 30%</div>
        </div>
      )}
    </div>
  );
}
