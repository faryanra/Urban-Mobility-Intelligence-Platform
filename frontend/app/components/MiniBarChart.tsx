"use client";

interface Bar {
  label: string;
  value: number;
  color?: string;
}

interface Props {
  data: Bar[];
  title: string;
  formatValue?: (v: number) => string;
}

export default function MiniBarChart({ data, title, formatValue }: Props) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map(d => d.value));

  return (
    <div className="mt-3">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        {title}
      </p>
      <div className="space-y-1.5">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="text-xs text-slate-400 w-16 truncate shrink-0">{d.label}</span>
            <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${max > 0 ? (d.value / max) * 100 : 0}%`,
                  backgroundColor: d.color || "#4ECDC4",
                }}
              />
            </div>
            <span className="text-xs text-slate-300 w-12 text-right shrink-0">
              {formatValue ? formatValue(d.value) : d.value.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
