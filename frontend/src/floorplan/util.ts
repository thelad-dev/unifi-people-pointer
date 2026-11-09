// Assumed real width of a plan without a calibrated width (meters); same
// default as the integration (FLOORPLAN_DEFAULT_WIDTH_M).
export const DEFAULT_WIDTH_M = 15;

// Distinct, readable marker colors on light floor plans.
const PALETTE = ['#1e88e5', '#d81b60', '#43a047', '#fb8c00', '#8e24aa', '#00897b', '#6d4c41', '#3949ab'];

// Colors follow the order of the configured persons, so they stay put while
// people come and go and differ for up to eight persons.
export function personColors(ids: string[]): (id: string) => string {
  const index = new Map(ids.map((id, i) => [id, i]));
  return (id: string) => {
    let slot = index.get(id);
    if (slot === undefined) {
      slot = 0;
      for (const char of id) slot = (slot * 31 + char.charCodeAt(0)) >>> 0;
    }
    return PALETTE[slot % PALETTE.length];
  };
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStored(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage unavailable: the choice lasts for this page only.
  }
}

// Sequential heat ramp, cool to hot; readable on light floor plans.
const HEAT_STOPS: [number, [number, number, number]][] = [
  [0, [44, 123, 182]],
  [0.25, [0, 166, 202]],
  [0.5, [144, 235, 157]],
  [0.75, [249, 208, 87]],
  [1, [215, 25, 28]],
];

export function heatColor(t: number): string {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0));
  for (let i = 1; i < HEAT_STOPS.length; i++) {
    const [p1, c1] = HEAT_STOPS[i];
    const [p0, c0] = HEAT_STOPS[i - 1];
    if (x <= p1) {
      const f = (x - p0) / (p1 - p0);
      const c = c0.map((v, k) => Math.round(v + (c1[k] - v) * f));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return 'rgb(215, 25, 28)';
}

export const HEAT_GRADIENT = `linear-gradient(to right, ${HEAT_STOPS.map(([p, c]) => `rgb(${c.join(', ')}) ${p * 100}%`).join(', ')})`;

export function formatBytes(bytes: number, perSecond = false): string {
  const units = ['B', 'kB', 'MB', 'GB', 'TB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  const text = value >= 100 || unit === 0 ? Math.round(value).toString() : value.toFixed(1);
  return `${text} ${units[unit]}${perSecond ? '/s' : ''}`;
}
