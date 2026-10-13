"use client";
import MiniBarChart from "./MiniBarChart";

type CityType = "eu" | "us-austin" | "us-chicago";

function getCityType(city: string): CityType {
  if (city === "austin") return "us-austin";
  if (city === "chicago") return "us-chicago";
  return "eu";
}

const VEHICLE_COLORS: Record<string, string> = {
  scooter: "#F59E0B",
  bicycle: "#4ECDC4",
  moped:   "#A78BFA",
  car:     "#F87171",
};

interface Props {
  city: string;
  accessibilityStats?: {
    accessibility_mean: number;
    cell_count: number;
    stop_count: number;
    high_access_cells: number;
    low_access_cells: number;
  } | null;
  austinBreakdown?: {
    by_vehicle: { vehicle_type: string; count: number }[];
    by_month:   { month: number; count: number }[];
    by_hour:    { hour: number; count: number }[];
  } | null;
  austinOD?: Array<Record<string, unknown>> | null;
  chicagoSummary?: {
    trip_count: number;
    avg_duration_min: number;
    active_stations: number;
  } | null;
  wlcThreshold?: number;
  onWlcChange?: (v: number) => void;
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-800">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
  );
}

export default function StatsPanel({
  city,
  accessibilityStats,
  austinBreakdown,
  austinOD,
  chicagoSummary,
  wlcThreshold = 0,
  onWlcChange,
}: Props) {
  const cityType = getCityType(city);

  if (cityType === "eu") {
    if (!accessibilityStats) {
      return <div className="p-4 text-slate-500 text-sm">Loading accessibility data…</div>;
    }
    const mean = (accessibilityStats.accessibility_mean * 100).toFixed(1);
    return (
      <div className="p-4 space-y-1">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Transit Accessibility
        </p>

        {/* WLC threshold filter slider */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-slate-400 uppercase tracking-wide">
              Show gaps: WLC below
            </span>
            <span className="text-xs font-mono text-teal-400">
              {wlcThreshold === 0 ? "all" : wlcThreshold.toFixed(2)}
            </span>
          </div>
          <input
            type="range"
            min={0} max={1} step={0.05}
            value={wlcThreshold}
            onChange={e => onWlcChange?.(Number(e.target.value))}
            className="w-full h-1 accent-teal-500 cursor-pointer"
          />
          {wlcThreshold > 0 && (
            <p className="text-xs text-slate-500 mt-1">Showing underserved areas only</p>
          )}
        </div>

        <StatRow label="Mean score" value={`${mean}%`} />
        <StatRow label="Transit stops" value={accessibilityStats.stop_count.toLocaleString()} />
        <StatRow label="High-access cells" value={accessibilityStats.high_access_cells.toLocaleString()} />
        <StatRow label="Low-access cells" value={accessibilityStats.low_access_cells.toLocaleString()} />
        <StatRow label="Grid cells total" value={accessibilityStats.cell_count.toLocaleString()} />
        <div className="mt-4 p-3 bg-slate-800 rounded-lg">
          <p className="text-xs text-slate-300 leading-relaxed">
            Dense transit coverage — WLC score combines stop proximity (70%)
            and population density (30%).
          </p>
        </div>
      </div>
    );
  }

  if (cityType === "us-austin") {
    const totalTrips = austinBreakdown?.by_vehicle.reduce((s, v) => s + Number(v.count), 0) || 0;
    const vehicleData = (austinBreakdown?.by_vehicle || []).map(v => ({
      label: v.vehicle_type,
      value: Number(v.count),
      color: VEHICLE_COLORS[v.vehicle_type] || "#94A3B8",
    }));
    const peakHour = austinBreakdown?.by_hour.reduce(
      (max, h) => Number(h.count) > Number(max.count) ? h : max,
      { hour: 0, count: 0 }
    );
    const hourlyData = (austinBreakdown?.by_hour || []).map(h => ({
      label: `${h.hour}h`,
      value: Number(h.count),
      color: Number(h.count) === Number(peakHour?.count) ? "#F59E0B" : "#4ECDC4",
    }));

    return (
      <div className="p-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Micromobility Trips
        </p>
        <StatRow label="Total trips" value={totalTrips.toLocaleString()} />
        <StatRow label="Period" value="Oct 2021" />
        {peakHour && <StatRow label="Peak hour" value={`${peakHour.hour}:00`} />}
        {austinOD && <StatRow label="O-D district flows" value={austinOD.length} />}
        <MiniBarChart data={vehicleData} title="By Vehicle Type" />
        <MiniBarChart
          data={hourlyData.filter((_, i) => i % 2 === 0)}
          title="Trips by Hour"
          formatValue={v => v > 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)}
        />
        <div className="mt-3">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Map Layers
          </p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm border border-amber-400 opacity-70" />
              <span className="text-xs text-slate-300">Council districts</span>
            </div>
            {austinOD && austinOD.length > 0 && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-amber-400 rounded" />
                <span className="text-xs text-slate-300">O-D flow arcs</span>
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 p-3 bg-slate-800 rounded-lg">
          <p className="text-xs text-slate-300 leading-relaxed">
            Arc lines show inter-district O-D flows. District 9 (downtown)
            dominates both origin and destination traffic.
          </p>
        </div>
      </div>
    );
  }

  if (cityType === "us-chicago") {
    return (
      <div className="p-4">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Divvy Bike-Share · 2013
        </p>
        {chicagoSummary ? (
          <>
            <StatRow label="Total trips" value={chicagoSummary.trip_count.toLocaleString()} />
            <StatRow label="Avg duration" value={`${chicagoSummary.avg_duration_min} min`} />
            <StatRow label="Active stations" value={chicagoSummary.active_stations.toLocaleString()} />
          </>
        ) : (
          <div className="text-slate-500 text-sm">Loading…</div>
        )}
        <div className="mt-4 p-3 bg-slate-800 rounded-lg">
          <p className="text-xs text-slate-300 leading-relaxed">
            Arc lines show top 30 station-to-station flows. Divvy stations
            cluster near CTA L train stops — classic first/last-mile pattern.
          </p>
        </div>
        <div className="mt-3">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Map Layers
          </p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 bg-amber-400 rounded" />
              <span className="text-xs text-slate-300">O-D flow arcs</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-400" />
              <span className="text-xs text-slate-300">CTA L train lines</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-teal-400" />
              <span className="text-xs text-slate-300">Divvy stations</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
