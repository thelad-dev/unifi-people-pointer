import type { ApUsage, Floor, UsageData, UsagePeriod } from '../api';
import type { HeatSpot } from './FloorMap';
import { HEAT_GRADIENT, formatBytes, heatColor } from './util';

export type HeatMetric = 'clients' | 'bytes';

export const PERIODS: { id: UsagePeriod; label: string }[] = [
  { id: 'now', label: 'Now' },
  { id: '1h', label: '1 h' },
  { id: '24h', label: '24 h' },
  { id: '7d', label: '7 d' },
];

function value(ap: ApUsage, metric: HeatMetric): number {
  return metric === 'bytes' ? ap.bytes ?? 0 : ap.clients;
}

export function formatValue(usage: UsageData, metric: HeatMetric, amount: number): string {
  if (metric === 'bytes') return formatBytes(amount, usage.bytes_unit === 'B/s');
  if (usage.period === 'now') return String(Math.round(amount));
  return amount.toFixed(1);
}

// Spots of one floor, scaled against the busiest AP of the whole house so
// floors stay comparable.
export function heatSpots(usage: UsageData, metric: HeatMetric, floor: Floor): HeatSpot[] {
  const max = Math.max(0, ...usage.aps.map((ap) => value(ap, metric)));
  return usage.aps
    .filter((ap) => ap.floor === floor.id && ap.x !== null && ap.y !== null)
    .map((ap) => ({
      mac: ap.mac,
      x: ap.x as number,
      y: ap.y as number,
      level: max > 0 ? value(ap, metric) / max : 0,
      label: formatValue(usage, metric, value(ap, metric)),
    }));
}

function describe(usage: UsageData, metric: HeatMetric): string {
  const what = metric === 'bytes' ? (usage.period === 'now' ? 'Current data rate' : 'Data moved') : usage.period === 'now' ? 'Wireless clients right now' : 'Average wireless clients';
  const span = { now: '', '1h': ' in the last hour', '24h': ' in the last 24 hours', '7d': ' in the last 7 days' }[usage.period];
  return `${what}${span} per access point.`;
}

interface PanelProps {
  usage: UsageData | null;
  metric: HeatMetric;
  floors: Floor[];
  error: string | null;
}

export function HeatmapPanel({ usage, metric, floors, error }: PanelProps) {
  if (!usage) {
    return (
      <div className="card side-card">
        <h3>Access point usage</h3>
        {error ? <div className="error">{error}</div> : <p className="muted small">Loading usage...</p>}
      </div>
    );
  }
  const max = Math.max(0, ...usage.aps.map((ap) => value(ap, metric)));
  const ranked = [...usage.aps].sort((a, b) => value(b, metric) - value(a, metric));
  const floorName = (id: string | null) => floors.find((f) => f.id === id)?.name;
  const noHistory = usage.period !== 'now' && usage.samples === 0;
  return (
    <div className="card side-card" data-testid="heatmap-panel">
      <h3>Access point usage</h3>
      <p className="muted small">{describe(usage, metric)}</p>
      <div className="heat-legend" aria-hidden="true">
        <span className="heat-legend-bar" style={{ background: HEAT_GRADIENT }} />
        <span className="heat-legend-scale">
          <span>{formatValue(usage, metric, 0)}</span>
          <span>{formatValue(usage, metric, max)}</span>
        </span>
      </div>
      {noHistory ? (
        <p className="muted small">No history yet; it builds up with every UniFi poll.</p>
      ) : (
        <ol className="usage-list">
          {ranked.map((ap) => {
            const amount = value(ap, metric);
            const share = max > 0 ? amount / max : 0;
            const where = floorName(ap.floor);
            return (
              <li key={ap.mac}>
                <span className="usage-name">
                  {ap.name || ap.mac}
                  <span className="muted small"> {where ? `on ${where}` : 'not placed'}</span>
                </span>
                <span className="usage-value">{formatValue(usage, metric, amount)}</span>
                <span className="usage-bar" aria-hidden="true">
                  <span style={{ width: `${share * 100}%`, background: heatColor(share) }} />
                </span>
              </li>
            );
          })}
        </ol>
      )}
      <p className="legend muted small">
        Only counters per access point are kept (5-minute steps for a day, hourly for a week), nothing about persons
        or devices.
        {metric === 'bytes' && ' Data is estimated from the client rates UniFi reports at each poll.'}
      </p>
    </div>
  );
}
