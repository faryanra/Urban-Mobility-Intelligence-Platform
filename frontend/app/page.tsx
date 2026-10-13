"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import StatsPanel from "./components/StatsPanel";
import {
  fetchAccessibility,
  fetchAccessibilityStats,
  fetchAustinDistricts,
  fetchAustinBreakdown,
  fetchAustinOD,
  fetchChicagoWards,
  fetchChicagoMetro,
  fetchChicagoOD,
  fetchChicagoSummary,
  fetchChicagoStations,
} from "@/lib/api";

const MapView = dynamic(() => import("./components/MapView"), { ssr: false });

const CITIES = [
  { id: "stockholm", label: "Stockholm", flag: "🇸🇪", type: "eu" },
  { id: "amsterdam", label: "Amsterdam", flag: "🇳🇱", type: "eu" },
  { id: "austin",    label: "Austin",    flag: "🇺🇸", type: "us" },
  { id: "chicago",   label: "Chicago",   flag: "🇺🇸", type: "us" },
];

export default function Home() {
  const [city, setCity] = useState("stockholm");
  const [wlcThreshold, setWlcThreshold] = useState<number>(0);
  const [showCatchmentHint, setShowCatchmentHint] = useState(true);

  const [accessibilityData, setAccessibilityData]   = useState<GeoJSON.FeatureCollection | null>(null);
  const [accessibilityStats, setAccessibilityStats] = useState<Record<string, unknown> | null>(null);

  const [austinDistricts, setAustinDistricts] = useState<GeoJSON.FeatureCollection | null>(null);
  const [austinBreakdown, setAustinBreakdown] = useState<Record<string, unknown> | null>(null);
  const [austinOD,        setAustinOD]        = useState<Array<Record<string, unknown>> | null>(null);

  const [chicagoWards,    setChicagoWards]    = useState<GeoJSON.FeatureCollection | null>(null);
  const [chicagoMetro,    setChicagoMetro]    = useState<GeoJSON.FeatureCollection | null>(null);
  const [chicagoOD,       setChicagoOD]       = useState<Array<Record<string, unknown>> | null>(null);
  const [chicagoSummary,  setChicagoSummary]  = useState<Record<string, unknown> | null>(null);
  const [chicagoStations, setChicagoStations] = useState<GeoJSON.FeatureCollection | null>(null);

  useEffect(() => {
    setAccessibilityData(null);
    setAccessibilityStats(null);
    setAustinDistricts(null);
    setAustinBreakdown(null);
    setAustinOD(null);
    setChicagoWards(null);
    setChicagoMetro(null);
    setChicagoOD(null);
    setChicagoSummary(null);
    setChicagoStations(null);
    setWlcThreshold(0);
    setShowCatchmentHint(true);

    if (city === "stockholm" || city === "amsterdam") {
      Promise.all([fetchAccessibility(city), fetchAccessibilityStats(city)])
        .then(([a, s]) => { setAccessibilityData(a); setAccessibilityStats(s); })
        .catch(console.error);
    }

    if (city === "austin") {
      Promise.all([fetchAustinDistricts(), fetchAustinBreakdown(), fetchAustinOD()])
        .then(([d, b, od]) => { setAustinDistricts(d); setAustinBreakdown(b); setAustinOD(od); })
        .catch(console.error);
    }

    if (city === "chicago") {
      Promise.all([
        fetchChicagoWards(),
        fetchChicagoMetro(),
        fetchChicagoOD(),
        fetchChicagoSummary(),
        fetchChicagoStations(),
      ])
        .then(([w, m, od, s, st]) => {
          setChicagoWards(w);
          setChicagoMetro(m);
          setChicagoOD(od);
          setChicagoSummary(s);
          setChicagoStations(st);
        })
        .catch(console.error);
    }
  }, [city]);

  const cityMeta = CITIES.find(c => c.id === city)!;
  const isEU = cityMeta.type === "eu";

  return (
    <main className="flex h-screen bg-gray-950 text-white overflow-hidden">
      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 overflow-y-auto">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xs font-bold tracking-widest text-gray-400 uppercase mb-1">
            Urban Mobility Intelligence
          </h1>
          <p className="text-xs text-gray-600">
            {isEU ? "European Transit" : "US Micromobility"}
          </p>
        </div>

        {/* City switcher */}
        <div className="p-4 border-b border-gray-800">
          <div className="grid grid-cols-2 gap-1.5">
            {CITIES.map(c => {
              const active = c.id === city;
              const teal = "bg-emerald-600 text-white";
              const amber = "bg-amber-600 text-white";
              const inactive = "bg-gray-800 text-gray-400 hover:bg-gray-700";
              const activeClass = active ? (c.type === "eu" ? teal : amber) : inactive;
              return (
                <button
                  key={c.id}
                  onClick={() => setCity(c.id)}
                  className={`py-2 px-2 rounded text-xs font-medium transition-colors text-center ${activeClass}`}
                >
                  <span className="mr-1">{c.flag}</span>{c.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Stats panel */}
        <div className="flex-1">
          <StatsPanel
            city={city}
            accessibilityStats={accessibilityStats as Parameters<typeof StatsPanel>[0]["accessibilityStats"]}
            austinBreakdown={austinBreakdown as Parameters<typeof StatsPanel>[0]["austinBreakdown"]}
            austinOD={austinOD}
            chicagoSummary={chicagoSummary as Parameters<typeof StatsPanel>[0]["chicagoSummary"]}
            wlcThreshold={wlcThreshold}
            onWlcChange={setWlcThreshold}
          />
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <MapView
          city={city}
          accessibilityData={accessibilityData}
          austinDistricts={austinDistricts}
          austinOD={austinOD}
          chicagoWards={chicagoWards}
          chicagoMetro={chicagoMetro}
          chicagoOD={chicagoOD}
          chicagoStations={chicagoStations}
          wlcThreshold={wlcThreshold}
        />

        {/* Walking catchment hint banner */}
        {(city === "stockholm" || city === "amsterdam") && showCatchmentHint && (
          <div
            className="absolute bottom-20 left-1/2 -translate-x-1/2 z-10
                       bg-slate-900/90 text-slate-300 text-xs px-4 py-2
                       rounded-full border border-slate-700 cursor-pointer
                       hover:bg-slate-800 transition whitespace-nowrap"
            onClick={() => setShowCatchmentHint(false)}
          >
            Click any transit stop to show 500m walking catchment &nbsp;✕
          </div>
        )}
      </div>
    </main>
  );
}
