"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { BASE } from "../../lib/api";

if (typeof window !== "undefined") {
  setWorkerUrl("/maplibre-gl-worker.mjs");
}

const CITY_CONFIG: Record<string, { center: [number, number]; zoom: number }> = {
  stockholm: { center: [18.07, 59.33], zoom: 11 },
  amsterdam: { center: [4.90, 52.37], zoom: 12 },
  austin:    { center: [-97.74, 30.27], zoom: 11 },
  chicago:   { center: [-87.65, 41.84], zoom: 11 },
};

function buildArcGeoJSON(flows: Array<{
  from_lat: number; from_lng: number;
  to_lat: number;   to_lng: number;
  flow_count: number;
  from_station_id?: string | number;
  to_station_id?: string | number;
}>) {
  if (!flows.length) return { type: "FeatureCollection" as const, features: [] };
  const maxFlow = Math.max(...flows.map(f => Number(f.flow_count)));
  const features = flows.map(f => {
    const fx = Number(f.from_lng), fy = Number(f.from_lat);
    const tx = Number(f.to_lng),   ty = Number(f.to_lat);
    const mx = (fx + tx) / 2, my = (fy + ty) / 2;
    const dx = tx - fx, dy = ty - fy;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    const offset = Math.min(len * 0.4, 0.05);
    const cx = mx + (-dy / len) * offset;
    const cy = my + ( dx / len) * offset;
    const coords: [number, number][] = [];
    for (let i = 0; i <= 20; i++) {
      const t = i / 20;
      const x = (1-t)*(1-t)*fx + 2*(1-t)*t*cx + t*t*tx;
      const y = (1-t)*(1-t)*fy + 2*(1-t)*t*cy + t*t*ty;
      coords.push([x, y]);
    }
    return {
      type: "Feature" as const,
      geometry: { type: "LineString" as const, coordinates: coords },
      properties: {
        flow_count: Number(f.flow_count),
        weight: maxFlow > 0 ? Number(f.flow_count) / maxFlow : 0,
        from_station_id: f.from_station_id ?? null,
        to_station_id:   f.to_station_id   ?? null,
      },
    };
  });
  return { type: "FeatureCollection" as const, features };
}

function parseGeometry(raw: unknown): GeoJSON.Geometry | null {
  if (!raw) return null;
  if (typeof raw === "string") {
    try { return JSON.parse(raw); } catch { return null; }
  }
  return raw as GeoJSON.Geometry;
}

interface MapViewProps {
  city: string;
  accessibilityData?: GeoJSON.FeatureCollection | null;
  austinDistricts?: GeoJSON.FeatureCollection | null;
  austinOD?: Array<Record<string, unknown>> | null;
  chicagoWards?: GeoJSON.FeatureCollection | null;
  chicagoMetro?: GeoJSON.FeatureCollection | null;
  chicagoOD?: Array<Record<string, unknown>> | null;
  chicagoStations?: GeoJSON.FeatureCollection | null;
  wlcThreshold?: number;
}

export default function MapView({
  city,
  accessibilityData,
  austinDistricts,
  austinOD,
  chicagoWards,
  chicagoMetro,
  chicagoOD,
  chicagoStations,
  wlcThreshold = 0,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  const cfg = CITY_CONFIG[city] ?? CITY_CONFIG.stockholm;

  useEffect(() => {
    setMapLoaded(false);
  }, [city]);

  // Apply WLC threshold filter whenever it changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("accessibility-fill")) return;
    if (wlcThreshold === 0) {
      map.setFilter("accessibility-fill", null);
      map.setFilter("accessibility-outline", null);
    } else {
      const f = ["<", ["get", "accessibility"], wlcThreshold] as maplibregl.FilterSpecification;
      map.setFilter("accessibility-fill", f);
      if (map.getLayer("accessibility-outline")) map.setFilter("accessibility-outline", f);
    }
  }, [wlcThreshold]);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: cfg.center,
      zoom: cfg.zoom,
    });
    mapRef.current = map;

    // Shared popup (one instance per map)
    const popup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "mobility-popup",
    });

    let done = false;
    const addLayers = () => {
      if (done) return;
      done = true;
      setMapLoaded(true);

      try {
        if (city === "stockholm" || city === "amsterdam") {
          if (accessibilityData && !map.getSource("accessibility")) {
            map.addSource("accessibility", { type: "geojson", data: accessibilityData });
            map.addLayer({
              id: "accessibility-fill",
              type: "fill",
              source: "accessibility",
              paint: {
                "fill-color": [
                  "interpolate", ["linear"], ["get", "accessibility"],
                  0.0, "#1e3a5f",
                  0.3, "#0d6e6e",
                  0.6, "#0d9488",
                  0.8, "#a3e635",
                  1.0, "#fde68a",
                ],
                "fill-opacity": 0.65,
              },
            });
            map.addLayer({
              id: "accessibility-outline",
              type: "line",
              source: "accessibility",
              paint: {
                "line-color": "#0d9488",
                "line-width": 0.3,
                "line-opacity": 0.3,
              },
            });

            // H3 cell hover popup
            map.on("mousemove", "accessibility-fill", (e) => {
              if (!e.features?.length) return;
              const f = e.features[0].properties as Record<string, unknown>;
              const score   = Number(f.accessibility  ?? 0).toFixed(3);
              const transit = Number(f.transit_score  ?? 0).toFixed(3);
              const density = Number(f.density_score  ?? 0).toFixed(3);
              popup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="popup-content">
                    <div class="popup-title">Accessibility Cell</div>
                    <div class="popup-row"><span>WLC Score</span><strong>${score}</strong></div>
                    <div class="popup-row"><span>Transit (70%)</span><strong>${transit}</strong></div>
                    <div class="popup-row"><span>Population (30%)</span><strong>${density}</strong></div>
                  </div>
                `)
                .addTo(map);
              map.getCanvas().style.cursor = "crosshair";
            });
            map.on("mouseleave", "accessibility-fill", () => {
              popup.remove();
              map.getCanvas().style.cursor = "";
            });
          }

          if (!map.getSource("stops-mvt")) {
            map.addSource("stops-mvt", {
              type: "vector",
              tiles: [`${BASE}/api/tiles/stops/{z}/{x}/{y}.mvt?city=${city}`],
              minzoom: 0, maxzoom: 16,
            });

            // Wider invisible hit area for easier clicking
            map.addLayer({
              id: "stops-hitarea",
              type: "circle",
              source: "stops-mvt",
              "source-layer": "stops",
              paint: {
                "circle-radius": 10,
                "circle-opacity": 0,
                "circle-color": "#000",
              },
            });

            map.addLayer({
              id: "stops-layer",
              type: "circle",
              source: "stops-mvt",
              "source-layer": "stops",
              paint: {
                "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 14, 5],
                "circle-color": "#4ECDC4",
                "circle-opacity": 0.75,
                "circle-stroke-width": 0.5,
                "circle-stroke-color": "#ffffff",
              },
            });

            // Stop name tooltip
            map.on("mousemove", "stops-layer", (e) => {
              if (!e.features?.length) return;
              const f = e.features[0].properties as Record<string, unknown>;
              popup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="popup-content">
                    <div class="popup-title">${String(f.stop_name ?? "Transit Stop")}</div>
                    <div class="popup-row"><span>Type</span><strong>${String(f.stop_type ?? "Stop")}</strong></div>
                  </div>
                `)
                .addTo(map);
              map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", "stops-layer", () => {
              popup.remove();
              map.getCanvas().style.cursor = "";
            });

            // Click hit area → walking catchment
            map.on("click", "stops-hitarea", async (e) => {
              const feature = e.features?.[0];
              if (!feature) return;
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const [lng, lat] = (feature.geometry as any).coordinates;

              if (map.getSource("catchment")) {
                if (map.getLayer("catchment-lines")) map.removeLayer("catchment-lines");
                map.removeSource("catchment");
              }

              const url = `${BASE}/api/catchment?lat=${lat}&lng=${lng}&city=${city}&radius_m=500`;
              try {
                const res = await fetch(url);
                const data = await res.json();
                map.addSource("catchment", { type: "geojson", data });
                map.addLayer({
                  id: "catchment-lines",
                  type: "line",
                  source: "catchment",
                  paint: {
                    "line-color": "#F59E0B",
                    "line-width": 2,
                    "line-opacity": 0.85,
                  },
                });
              } catch {
                // Catchment fetch failed silently
              }
            });
            map.on("mouseenter", "stops-hitarea", () => {
              map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", "stops-hitarea", () => {
              map.getCanvas().style.cursor = "";
            });
          }

          // Color legend
          const legend = document.createElement("div");
          legend.className = "map-legend";
          legend.innerHTML = `
            <div class="legend-title">WLC Accessibility Score</div>
            <div class="legend-gradient"></div>
            <div class="legend-labels">
              <span>0.0 Low</span><span>0.5</span><span>1.0 High</span>
            </div>
            <div class="legend-note">Transit (70%) + Population (30%)</div>
          `;
          map.getContainer().appendChild(legend);
        }

        if (city === "austin") {
          if (austinDistricts && (austinDistricts.features?.length ?? 0) > 0 && !map.getSource("districts")) {
            map.addSource("districts", { type: "geojson", data: austinDistricts });
            map.addLayer({
              id: "districts-fill",
              type: "fill",
              source: "districts",
              paint: { "fill-color": "#F59E0B", "fill-opacity": 0.05 },
            });
            map.addLayer({
              id: "districts-outline",
              type: "line",
              source: "districts",
              paint: { "line-color": "#F59E0B", "line-width": 1.5, "line-opacity": 0.7 },
            });

            const labelFeatures = (austinDistricts.features ?? [])
              .map(f => {
                const centroid = parseGeometry(f.properties?.centroid);
                if (!centroid || centroid.type !== "Point") return null;
                return {
                  type: "Feature" as const,
                  geometry: centroid,
                  properties: { district_id: f.properties?.district_id ?? "" },
                };
              })
              .filter(Boolean) as GeoJSON.Feature[];

            if (labelFeatures.length > 0 && !map.getSource("district-labels")) {
              map.addSource("district-labels", {
                type: "geojson",
                data: { type: "FeatureCollection", features: labelFeatures },
              });
              map.addLayer({
                id: "district-label-text",
                type: "symbol",
                source: "district-labels",
                layout: {
                  "text-field": ["get", "district_id"],
                  "text-size": 12,
                  "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
                },
                paint: {
                  "text-color": "#F59E0B",
                  "text-halo-color": "#0f172a",
                  "text-halo-width": 1.5,
                },
              });
            }
          }

          if (austinOD && austinOD.length > 0 && !map.getSource("austin-od")) {
            const arcData = buildArcGeoJSON(
              austinOD.map((f) => ({
                from_lat:   Number(f.from_lat),
                from_lng:   Number(f.from_lng),
                to_lat:     Number(f.to_lat),
                to_lng:     Number(f.to_lng),
                flow_count: Number(f.flow_count),
              }))
            );
            map.addSource("austin-od", { type: "geojson", data: arcData });
            map.addLayer({
              id: "austin-od-arcs",
              type: "line",
              source: "austin-od",
              paint: {
                "line-color": "#F59E0B",
                "line-opacity": ["interpolate", ["linear"], ["get", "weight"], 0, 0.2, 1, 0.85],
                "line-width":   ["interpolate", ["linear"], ["get", "weight"], 0, 0.5, 1, 3.5],
              },
            });
          }
        }

        if (city === "chicago") {
          // Layer order: ward fills → metro lines → stations → OD arcs
          if (chicagoWards && !map.getSource("wards")) {
            map.addSource("wards", { type: "geojson", data: chicagoWards });
            map.addLayer({
              id: "wards-fill",
              type: "fill",
              source: "wards",
              paint: { "fill-color": "#1e293b", "fill-opacity": 0.4 },
            });
            map.addLayer({
              id: "wards-outline",
              type: "line",
              source: "wards",
              paint: { "line-color": "#334155", "line-width": 0.8 },
            });
          }

          if (chicagoMetro && !map.getSource("metro")) {
            const metroFC = chicagoMetro as GeoJSON.FeatureCollection;
            const normalizedMetro = (metroFC.features ?? [])
              .map(f => ({ ...f, geometry: parseGeometry(f.geometry) as GeoJSON.Geometry }))
              .filter(f => f.geometry !== null);
            map.addSource("metro", {
              type: "geojson",
              data: { type: "FeatureCollection", features: normalizedMetro },
            });
            map.addLayer({
              id: "chicago-metro-lines",
              type: "line",
              source: "metro",
              layout: { "line-join": "round", "line-cap": "round" },
              paint: {
                "line-color": "#EF4444",
                "line-width": 2.5,
                "line-opacity": 0.9,
              },
            });
          }

          if (chicagoStations && !map.getSource("stations")) {
            const fc = chicagoStations as GeoJSON.FeatureCollection;
            const normalizedFeatures = (fc.features ?? [])
              .map(f => ({
                ...f,
                geometry: parseGeometry(f.geometry) as GeoJSON.Geometry,
              }))
              .filter(f => f.geometry !== null);

            map.addSource("stations", {
              type: "geojson",
              data: { type: "FeatureCollection", features: normalizedFeatures },
            });
            map.addLayer({
              id: "chicago-stations",
              type: "circle",
              source: "stations",
              paint: {
                "circle-radius": 4,
                "circle-color": "#4ECDC4",
                "circle-opacity": 0.8,
                "circle-stroke-width": 0.5,
                "circle-stroke-color": "#ffffff",
              },
            });

            map.on("mousemove", "chicago-stations", (e) => {
              if (!e.features?.length) return;
              const f = e.features[0].properties as Record<string, unknown>;
              popup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="popup-content">
                    <div class="popup-title">Divvy Station</div>
                    <div class="popup-row"><span>Station ID</span><strong>${String(f.station_id ?? "—")}</strong></div>
                    <div class="popup-row"><span>Name</span><strong>${String(f.name ?? "Unknown")}</strong></div>
                  </div>
                `)
                .addTo(map);
              map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", "chicago-stations", () => {
              popup.remove();
              map.getCanvas().style.cursor = "";
            });
          }

          if (chicagoOD && chicagoOD.length > 0 && !map.getSource("od-arcs")) {
            const arcGeoJSON = buildArcGeoJSON(
              (chicagoOD as Array<Record<string, unknown>>).map(f => ({
                from_lat: Number(f.from_lat),
                from_lng: Number(f.from_lng),
                to_lat:   Number(f.to_lat),
                to_lng:   Number(f.to_lng),
                flow_count: Number(f.flow_count),
                from_station_id: String(f.from_station_id ?? ""),
                to_station_id:   String(f.to_station_id   ?? ""),
              }))
            );
            map.addSource("od-arcs", { type: "geojson", data: arcGeoJSON });
            map.addLayer({
              id: "chicago-od-arcs",
              type: "line",
              source: "od-arcs",
              paint: {
                "line-color": "#F59E0B",
                "line-opacity": ["interpolate", ["linear"], ["get", "weight"], 0, 0.2, 1, 0.9],
                "line-width":  ["interpolate", ["linear"], ["get", "weight"], 0, 0.5, 1, 4],
              },
            });

            map.on("mousemove", "chicago-od-arcs", (e) => {
              if (!e.features?.length) return;
              const f = e.features[0].properties as Record<string, unknown>;
              popup
                .setLngLat(e.lngLat)
                .setHTML(`
                  <div class="popup-content">
                    <div class="popup-title">Trip Corridor</div>
                    <div class="popup-row"><span>From station</span><strong>${String(f.from_station_id ?? "—")}</strong></div>
                    <div class="popup-row"><span>To station</span><strong>${String(f.to_station_id ?? "—")}</strong></div>
                    <div class="popup-row"><span>Trips</span><strong>${String(f.flow_count ?? "—")}</strong></div>
                  </div>
                `)
                .addTo(map);
              map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", "chicago-od-arcs", () => {
              popup.remove();
              map.getCanvas().style.cursor = "";
            });
          }
        }
      } catch {
        // Style not ready — layers will be missing but map still renders
      }
    };

    map.once("load", addLayers);
    map.once("style.load", addLayers);
    map.once("render", addLayers);

    return () => {
      done = true;
      popup.remove();
      map.remove();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [city, accessibilityData, austinDistricts, austinOD, chicagoWards, chicagoMetro, chicagoOD, chicagoStations]);

  return (
    <div ref={containerRef} className="w-full h-full" style={{ position: "relative" }}>
      {!mapLoaded && (
        <div
          style={{
            position: "absolute", inset: 0, zIndex: 10,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "#0f172a", color: "#94a3b8", fontSize: "14px",
            pointerEvents: "none",
          }}
        >
          Loading map…
        </div>
      )}
    </div>
  );
}
