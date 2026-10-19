"use client";
import MiniBarChart from "./MiniBarChart";
import type { AccessibilityStats, AustinBreakdown, ChicagoSummary, FlowRow, LoadState } from "@/lib/api";

const VEHICLE_COLORS: Record<string, string> = {
  scooter: "#F59E0B",
  bicycle: "#4ECDC4",
  moped:   "#A78BFA",
  car:     "#F87171",
};

const pct = (part: number, whole: number) =>
  whole > 0 ? `${Math.round((part / whole) * 100)}%` : "0%";

function formatPeriod(start: string | null, end: string | null) {
  if (!start || !end) return "Unknown";
  const fmt = (d: string, opts: Intl.DateTimeFormatOptions) =>
    new Date(`${d}T00:00:00Z`).toLocaleDateString("en-GB", { timeZone: "UTC", ...opts });
  return `${fmt(start, { day: "numeric", month: "short" })} to ${fmt(end, {
    day: "numeric", month: "short", year: "numeric",
  })}`;
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-800">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{children}</p>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-4 p-3 bg-slate-800 rounded-lg">
      <p className="text-xs text-slate-300 leading-relaxed">{children}</p>
    </div>
  );
}

function LegendItem({ swatch, label }: { swatch: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className={swatch} />
      <span className="text-xs text-slate-300">{label}</span>
    </div>
  );
}

function EuPanel({ stats, wlcThreshold, onWlcChange }: {
  stats: AccessibilityStats; wlcThreshold: number; onWlcChange: (v: number) => void;
}) {
  return (
    <div className="p-4 space-y-1">
      <SectionTitle>Transit accessibility</SectionTitle>
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <label htmlFor="wlc" className="text-xs text-slate-400 uppercase tracking-wide">
            Show gaps: WLC below
          </label>
          <span className="text-xs font-mono text-teal-400">
            {wlcThreshold === 0 ? "all" : wlcThreshold.toFixed(2)}
          </span>
        </div>
        <input
          id="wlc"
          type="range"
          min={0} max={1} step={0.05}
          value={wlcThreshold}
          onChange={e => onWlcChange(Number(e.target.value))}
          className="w-full h-1 accent-teal-500 cursor-pointer"
        />
        {wlcThreshold > 0 && (
          <p className="text-xs text-slate-500 mt-1">Showing underserved cells only</p>
        )}
      </div>
      <StatRow label="Mean WLC score" value={stats.accessibility_mean.toFixed(2)} />
      <StatRow label="Transit stops" value={stats.stop_count.toLocaleString()} />
      <StatRow label="Cells scoring 0.7 or more" value={stats.high_access_cells.toLocaleString()} />
      <StatRow label="Cells scoring below 0.3" value={stats.low_access_cells.toLocaleString()} />
      <StatRow label="Grid cells (500 m)" value={stats.cell_count.toLocaleString()} />
      <Note>
        {pct(stats.low_access_cells, stats.cell_count)} of cells score below 0.3, and{" "}
        {pct(stats.cells_beyond_500m, stats.cell_count)} have their centre more than 500 m
        (straight line) from the nearest stop. Score = 0.7 x transit proximity + 0.3 x
        population density.
      </Note>
    </div>
  );
}

function busiestDistrict(od: FlowRow[]) {
  const totals = new Map<string, number>();
  let all = 0;
  for (const f of od) {
    all += Number(f.flow_count);
    for (const d of new Set([f.from_district, f.to_district])) {
      if (d) totals.set(d, (totals.get(d) ?? 0) + Number(f.flow_count));
    }
  }
  const [district, trips] = [...totals.entries()].sort((a, b) => b[1] - a[1])[0] ?? ["", 0];
  return { district, share: pct(trips, all) };
}

function AustinPanel({ breakdown, od }: { breakdown: AustinBreakdown; od: FlowRow[] }) {
  const totalTrips = breakdown.by_vehicle.reduce((s, v) => s + Number(v.count), 0);
  const vehicleData = breakdown.by_vehicle.map(v => ({
    label: v.vehicle_type,
    value: Number(v.count),
    color: VEHICLE_COLORS[v.vehicle_type] ?? "#94A3B8",
  }));
  const counts = Array.from({ length: 24 }, (_, h) =>
    Number(breakdown.by_hour.find(r => r.hour === h)?.count ?? 0));
  const peakHour = counts.indexOf(Math.max(...counts));
  const bins = Array.from({ length: 12 }, (_, i) => ({
    label: `${String(i * 2).padStart(2, "0")}-${String(i * 2 + 1).padStart(2, "0")}h`,
    value: counts[i * 2] + counts[i * 2 + 1],
    color: Math.floor(peakHour / 2) === i ? "#F59E0B" : "#4ECDC4",
  }));
  const hub = busiestDistrict(od);

  return (
    <div className="p-4">
      <SectionTitle>Micromobility trips</SectionTitle>
      <StatRow label="Total trips" value={totalTrips.toLocaleString()} />
      <StatRow label="Period" value={formatPeriod(breakdown.period.start, breakdown.period.end)} />
      <StatRow label="Peak hour (local)" value={`${String(peakHour).padStart(2, "0")}:00`} />
      <StatRow label="District flows shown" value={od.length} />
      <MiniBarChart data={vehicleData} title="By vehicle type" />
      <MiniBarChart
        data={bins}
        title="Trips by hour (Austin time)"
        formatValue={v => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v))}
      />
      <div className="mt-3">
        <SectionTitle>Map layers</SectionTitle>
        <div className="space-y-1.5">
          <LegendItem swatch="w-3 h-3 rounded-sm border border-amber-400 opacity-70" label="Council districts" />
          <LegendItem swatch="w-3 h-0.5 bg-amber-400 rounded" label="District to district flows" />
        </div>
      </div>
      <Note>
        {hub.district && <>District {hub.district} is an endpoint of {hub.share} of trips in the
          30 busiest inter-district flows. </>}
        The public dataset reports trip ends by council district, so arcs connect district
        centroids rather than exact coordinates.
      </Note>
    </div>
  );
}

function ChicagoPanel({ summary }: { summary: ChicagoSummary }) {
  return (
    <div className="p-4">
      <SectionTitle>Divvy bike share</SectionTitle>
      <StatRow label="Trips" value={summary.trip_count.toLocaleString()} />
      <StatRow label="Period" value={formatPeriod(summary.period_start, summary.period_end)} />
      <StatRow label="Median duration" value={`${summary.median_duration_min} min`} />
      <StatRow label="Stations used" value={summary.active_stations.toLocaleString()} />
      <div className="mt-3">
        <SectionTitle>Map layers</SectionTitle>
        <div className="space-y-1.5">
          <LegendItem swatch="w-3 h-0.5 bg-amber-400 rounded" label="Busiest station flows" />
          <LegendItem swatch="w-3 h-0.5 bg-red-400 rounded" label="CTA L train lines" />
          <LegendItem swatch="w-2 h-2 rounded-full bg-teal-400" label="Divvy stations" />
        </div>
      </div>
      <Note>
        Arcs show the 30 busiest station-to-station flows in the first weeks of the Divvy
        system (summer 2013), drawn against the CTA L network.
      </Note>
    </div>
  );
}

interface Props {
  state: LoadState;
  wlcThreshold: number;
  onWlcChange: (v: number) => void;
  onRetry: () => void;
}

export default function StatsPanel({ state, wlcThreshold, onWlcChange, onRetry }: Props) {
  if (state.status === "loading") {
    return <div className="p-4 text-slate-500 text-sm">Loading {state.city} data...</div>;
  }
  if (state.status === "error") {
    return (
      <div className="p-4 space-y-3" role="alert">
        <p className="text-sm text-red-300">Could not load {state.city} data.</p>
        <p className="text-xs text-slate-400">{state.error}</p>
        <button
          onClick={onRetry}
          className="text-xs px-3 py-1.5 rounded bg-slate-800 text-slate-200 hover:bg-slate-700"
        >
          Retry
        </button>
      </div>
    );
  }
  const { data } = state;
  if (data.kind === "eu") {
    return <EuPanel stats={data.stats} wlcThreshold={wlcThreshold} onWlcChange={onWlcChange} />;
  }
  if (data.kind === "austin") return <AustinPanel breakdown={data.breakdown} od={data.od} />;
  return <ChicagoPanel summary={data.summary} />;
}
