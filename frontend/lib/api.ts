export const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export async function fetchHealth() {
  const r = await fetch(`${BASE}/health`);
  return r.json();
}

export async function fetchAccessibility(city: string) {
  const r = await fetch(`${BASE}/api/accessibility?city=${city}`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchAccessibilityStats(city: string) {
  const r = await fetch(`${BASE}/api/accessibility/stats?city=${city}`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchAustinDistricts() {
  const r = await fetch(`${BASE}/api/districts/austin`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchAustinBreakdown() {
  const r = await fetch(`${BASE}/api/trips/breakdown?city=austin`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchAustinOD() {
  const r = await fetch(`${BASE}/api/od/austin`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchChicagoWards() {
  const r = await fetch(`${BASE}/api/districts/chicago`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchChicagoOD() {
  const r = await fetch(`${BASE}/api/od/chicago`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchChicagoMetro() {
  const r = await fetch(`${BASE}/api/metro/chicago`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchChicagoSummary() {
  const r = await fetch(`${BASE}/api/trips/summary/chicago`);
  if (!r.ok) return null;
  return r.json();
}

export async function fetchChicagoStations() {
  const r = await fetch(`${BASE}/api/stations?city=chicago`);
  if (!r.ok) return null;
  return r.json();
}
