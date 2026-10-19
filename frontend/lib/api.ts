export const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export type City = "stockholm" | "amsterdam" | "austin" | "chicago";
export type EuCity = "stockholm" | "amsterdam";

export const isEuCity = (city: City): city is EuCity =>
  city === "stockholm" || city === "amsterdam";

export interface AccessibilityStats {
  cell_count: number;
  accessibility_mean: number;
  high_access_cells: number;
  low_access_cells: number;
  cells_beyond_500m: number;
  stop_count: number;
}

export interface FlowRow {
  from_lat: number;
  from_lng: number;
  to_lat: number;
  to_lng: number;
  flow_count: number;
  from_station_id?: string;
  to_station_id?: string;
  from_station_name?: string;
  to_station_name?: string;
  from_district?: string;
  to_district?: string;
}

export interface AustinBreakdown {
  timezone: string;
  period: { start: string | null; end: string | null };
  by_vehicle: { vehicle_type: string; count: number }[];
  by_hour: { hour: number; count: number }[];
}

export interface ChicagoSummary {
  trip_count: number;
  median_duration_min: number;
  active_stations: number;
  period_start: string | null;
  period_end: string | null;
}

type FC = GeoJSON.FeatureCollection;

export type CityData =
  | { kind: "eu"; accessibility: FC; stats: AccessibilityStats }
  | { kind: "austin"; districts: FC; breakdown: AustinBreakdown; od: FlowRow[] }
  | { kind: "chicago"; wards: FC; metro: FC; stations: FC; od: FlowRow[]; summary: ChicagoSummary };

export type LoadState =
  | { city: City; status: "loading" }
  | { city: City; status: "ready"; data: CityData }
  | { city: City; status: "error"; error: string };

export class ApiError extends Error {}

async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("The API is unreachable. Check that the backend is running.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function loadCity(city: City, signal?: AbortSignal): Promise<CityData> {
  if (isEuCity(city)) {
    const [accessibility, stats] = await Promise.all([
      getJSON<FC>(`/api/accessibility?city=${city}`, signal),
      getJSON<AccessibilityStats>(`/api/accessibility/stats?city=${city}`, signal),
    ]);
    return { kind: "eu", accessibility, stats };
  }
  if (city === "austin") {
    const [districts, breakdown, od] = await Promise.all([
      getJSON<FC>("/api/districts/austin", signal),
      getJSON<AustinBreakdown>("/api/trips/breakdown?city=austin", signal),
      getJSON<FlowRow[]>("/api/od/austin", signal),
    ]);
    return { kind: "austin", districts, breakdown, od };
  }
  const [wards, metro, stations, od, summary] = await Promise.all([
    getJSON<FC>("/api/districts/chicago", signal),
    getJSON<FC>("/api/metro/chicago", signal),
    getJSON<FC>("/api/stations/chicago", signal),
    getJSON<FlowRow[]>("/api/od/chicago", signal),
    getJSON<ChicagoSummary>("/api/trips/summary/chicago", signal),
  ]);
  return { kind: "chicago", wards, metro, stations, od, summary };
}

export async function fetchCatchment(
  city: EuCity, lat: number, lng: number, signal?: AbortSignal,
): Promise<FC> {
  return getJSON<FC>(
    `/api/catchment?city=${city}&lat=${lat}&lng=${lng}&radius_m=500`, signal,
  );
}
