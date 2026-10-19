"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import StatsPanel from "./components/StatsPanel";
import { City, LoadState, isEuCity, loadCity } from "@/lib/api";

const MapView = dynamic(() => import("./components/MapView"), { ssr: false });

const CITIES: { id: City; label: string; flag: string; eu: boolean }[] = [
  { id: "stockholm", label: "Stockholm", flag: "🇸🇪", eu: true },
  { id: "amsterdam", label: "Amsterdam", flag: "🇳🇱", eu: true },
  { id: "austin",    label: "Austin",    flag: "🇺🇸", eu: false },
  { id: "chicago",   label: "Chicago",   flag: "🇺🇸", eu: false },
];

export default function Home() {
  const [city, setCity] = useState<City>("stockholm");
  const [attempt, setAttempt] = useState(0);
  const [load, setLoad] = useState<LoadState>({ city: "stockholm", status: "loading" });
  const [wlcThreshold, setWlcThreshold] = useState(0);
  const [showCatchmentHint, setShowCatchmentHint] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoad({ city, status: "loading" });
    loadCity(city, controller.signal)
      .then(data => setLoad({ city, status: "ready", data }))
      .catch((err: Error) => {
        if (!controller.signal.aborted) setLoad({ city, status: "error", error: err.message });
      });
    return () => controller.abort();
  }, [city, attempt]);

  const selectCity = (next: City) => {
    if (next === city) return;
    setCity(next);
    setWlcThreshold(0);
    setShowCatchmentHint(true);
  };

  const current: LoadState = load.city === city ? load : { city, status: "loading" };
  const data = current.status === "ready" ? current.data : null;
  const eu = isEuCity(city);

  return (
    <main className="flex flex-col-reverse md:flex-row h-[100dvh] bg-gray-950 text-white overflow-hidden">
      <aside className="flex-1 md:flex-none md:w-72 flex flex-col bg-gray-900 border-t md:border-t-0 md:border-r border-gray-800 overflow-y-auto">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xs font-bold tracking-widest text-gray-300 uppercase mb-1">
            Urban Mobility Intelligence
          </h1>
          <p className="text-xs text-gray-500">
            {eu ? "European transit accessibility" : "US micromobility flows"}
          </p>
        </div>

        <div className="p-4 border-b border-gray-800">
          <div className="grid grid-cols-4 md:grid-cols-2 gap-1.5">
            {CITIES.map(c => {
              const active = c.id === city;
              const activeClass = c.eu ? "bg-emerald-600 text-white" : "bg-amber-600 text-white";
              return (
                <button
                  key={c.id}
                  onClick={() => selectCity(c.id)}
                  aria-pressed={active}
                  className={`py-2 px-1 rounded text-xs font-medium transition-colors text-center ${
                    active ? activeClass : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  <span className="hidden md:inline mr-1">{c.flag}</span>{c.label}
                </button>
              );
            })}
          </div>
        </div>

        <StatsPanel
          state={current}
          wlcThreshold={wlcThreshold}
          onWlcChange={setWlcThreshold}
          onRetry={() => setAttempt(a => a + 1)}
        />
      </aside>

      <section className="relative h-[55dvh] md:h-auto md:flex-1 shrink-0">
        <MapView city={city} data={data} wlcThreshold={wlcThreshold} />

        {eu && data && showCatchmentHint && (
          <button
            className="absolute top-3 left-1/2 -translate-x-1/2 z-10 w-max max-w-[75%]
                       bg-slate-900/90 text-slate-300 text-xs px-4 py-2 rounded-full
                       border border-slate-700 hover:bg-slate-800 transition"
            onClick={() => setShowCatchmentHint(false)}
          >
            Select a stop to see its 500 m walking catchment &nbsp;✕
          </button>
        )}
      </section>
    </main>
  );
}
