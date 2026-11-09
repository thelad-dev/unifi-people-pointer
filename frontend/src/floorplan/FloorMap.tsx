import { useCallback, useLayoutEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, KeyboardEvent as ReactKeyboardEvent } from 'react';
import type { Floor, MapAccessPoint, MapPerson } from '../api';
import { useFloorImage } from './useFloorImage';
import { DEFAULT_WIDTH_M, heatColor, initials } from './util';

// One heat spot per AP on this floor: its share of the busiest AP (0..1)
// and the label shown under the AP.
export interface HeatSpot {
  mac: string;
  x: number;
  y: number;
  level: number;
  label: string;
}

interface Props {
  floor: Floor;
  aps: MapAccessPoint[];
  persons: MapPerson[];
  showAps: boolean;
  showPersons: boolean;
  editing: boolean;
  placing: string | null;
  onPlace: (mac: string, x: number, y: number) => void;
  colorOf: (personId: string) => string;
  heat?: HeatSpot[] | null;
}

// Below this width the map follows the width only and the page scrolls;
// wider layouts fit the whole plan into the visible height.
const FIT_HEIGHT_MIN_WIDTH = 600;
const MIN_FIT_HEIGHT = 320;
// Distance of person markers from their AP when several share one.
const FAN_RADIUS_PX = 26;
const KEY_STEP = 0.005;
// Real radius of a heat spot around its AP (meters).
const HEAT_RADIUS_M = 5;

function clamp(value: number) {
  return Math.min(1, Math.max(0, value));
}

function useStageSize(floor: Floor) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const measureRef = useRef<() => void>(() => undefined);

  // Controls above the map can appear or wrap without resizing the map
  // column; measure again after every render (no update when unchanged).
  useLayoutEffect(() => measureRef.current());

  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const measure = () => {
      const availWidth = wrap.clientWidth;
      if (!availWidth) return;
      let scale = availWidth / floor.width;
      if (availWidth >= FIT_HEIGHT_MIN_WIDTH) {
        const main = wrap.closest('.main-content');
        const bottom = main ? parseFloat(getComputedStyle(main).paddingBottom) || 0 : 0;
        const top = wrap.getBoundingClientRect().top + window.scrollY;
        const availHeight = Math.max(MIN_FIT_HEIGHT, window.innerHeight - top - bottom);
        scale = Math.min(scale, availHeight / floor.height);
      }
      const next = {
        width: Math.floor(floor.width * scale),
        height: Math.floor(floor.height * scale),
      };
      setSize((prev) => (prev && prev.width === next.width && prev.height === next.height ? prev : next));
    };
    measureRef.current = measure;
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(wrap);
    window.addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [floor.width, floor.height]);

  return { wrapRef, size };
}

function FloorMap({ floor, aps, persons, showAps, showPersons, editing, placing, onPlace, colorOf, heat }: Props) {
  const { wrapRef, size } = useStageSize(floor);
  const stageRef = useRef<HTMLDivElement>(null);
  const { src, error } = useFloorImage(floor.image_url);
  const [drag, setDrag] = useState<{ mac: string; x: number; y: number } | null>(null);

  const fraction = useCallback((clientX: number, clientY: number) => {
    const rect = stageRef.current!.getBoundingClientRect();
    return {
      x: clamp((clientX - rect.left) / rect.width),
      y: clamp((clientY - rect.top) / rect.height),
    };
  }, []);

  const onStageClick = (e: React.MouseEvent) => {
    if (!editing || !placing) return;
    const { x, y } = fraction(e.clientX, e.clientY);
    onPlace(placing, x, y);
  };

  const onApPointerDown = (e: ReactPointerEvent, ap: MapAccessPoint) => {
    if (!editing) return;
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDrag({ mac: ap.mac, x: ap.x ?? 0, y: ap.y ?? 0 });
  };

  const onApPointerMove = (e: ReactPointerEvent) => {
    if (!drag) return;
    setDrag({ mac: drag.mac, ...fraction(e.clientX, e.clientY) });
  };

  const onApPointerUp = () => {
    if (!drag) return;
    onPlace(drag.mac, drag.x, drag.y);
    setDrag(null);
  };

  const onApKey = (e: ReactKeyboardEvent, ap: MapAccessPoint) => {
    if (!editing) return;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-KEY_STEP, 0],
      ArrowRight: [KEY_STEP, 0],
      ArrowUp: [0, -KEY_STEP],
      ArrowDown: [0, KEY_STEP],
    };
    const move = moves[e.key];
    if (!move) return;
    e.preventDefault();
    onPlace(ap.mac, clamp((ap.x ?? 0) + move[0]), clamp((ap.y ?? 0) + move[1]));
  };

  const position = (ap: MapAccessPoint) =>
    drag && drag.mac === ap.mac ? { x: drag.x, y: drag.y } : { x: ap.x ?? 0, y: ap.y ?? 0 };

  // Persons sharing an AP fan out around it; one person sits on the AP.
  const byAp = new Map<string, MapPerson[]>();
  for (const person of persons) {
    byAp.set(person.ap_mac, [...(byAp.get(person.ap_mac) || []), person]);
  }
  const heatLabels = new Map((heat || []).map((spot) => [spot.mac, spot.label]));
  const widthM = floor.width_m || DEFAULT_WIDTH_M;
  const pxPerMeter = floor.width / widthM;

  return (
    <div className="map-wrap" ref={wrapRef}>
      {size && (
        <div
          className={`map-stage${editing && placing ? ' map-stage-placing' : ''}`}
          ref={stageRef}
          style={{ width: size.width, height: size.height }}
          onClick={onStageClick}
          data-testid="map-stage"
        >
          {src ? (
            <img src={src} alt={`Floor plan ${floor.name}`} draggable={false} />
          ) : (
            <div className="map-image-status">{error ? `Image failed: ${error}` : 'Loading floor plan...'}</div>
          )}
          {heat && (
            <svg
              className="map-overlay map-heat"
              viewBox={`0 0 ${floor.width} ${floor.height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                {heat.map((spot) => (
                  <radialGradient key={spot.mac} id={`heat-${spot.mac.replace(/:/g, '')}`}>
                    <stop offset="0%" stopColor={heatColor(spot.level)} stopOpacity={0.85} />
                    <stop offset="55%" stopColor={heatColor(spot.level)} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={heatColor(spot.level)} stopOpacity={0} />
                  </radialGradient>
                ))}
              </defs>
              {heat.map((spot) => (
                <circle
                  key={spot.mac}
                  className="heat-spot"
                  data-level={spot.level.toFixed(3)}
                  cx={spot.x * floor.width}
                  cy={spot.y * floor.height}
                  r={HEAT_RADIUS_M * pxPerMeter}
                  fill={`url(#heat-${spot.mac.replace(/:/g, '')})`}
                />
              ))}
            </svg>
          )}
          {showPersons && (
            <svg
              className="map-overlay"
              viewBox={`0 0 ${floor.width} ${floor.height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              {persons.map((person) => (
                <circle
                  key={person.id}
                  className="uncertainty"
                  cx={(person.x ?? 0) * floor.width}
                  cy={(person.y ?? 0) * floor.height}
                  r={person.radius_m * pxPerMeter}
                  style={{ fill: colorOf(person.id), stroke: colorOf(person.id) }}
                />
              ))}
            </svg>
          )}
          {(showAps || editing) &&
            aps.map((ap) => {
              const pos = position(ap);
              return (
                <button
                  key={ap.mac}
                  type="button"
                  className={`ap-marker${editing ? ' ap-marker-editing' : ''}${drag?.mac === ap.mac ? ' ap-marker-dragging' : ''}`}
                  style={{ left: `${pos.x * 100}%`, top: `${pos.y * 100}%` }}
                  title={`${ap.name || ap.mac} (${ap.clients} clients)`}
                  aria-label={`Access point ${ap.name || ap.mac}`}
                  onPointerDown={(e) => onApPointerDown(e, ap)}
                  onPointerMove={onApPointerMove}
                  onPointerUp={onApPointerUp}
                  onPointerCancel={() => setDrag(null)}
                  onKeyDown={(e) => onApKey(e, ap)}
                  onClick={(e) => e.stopPropagation()}
                  data-testid={`ap-${ap.mac}`}
                >
                  <span className="ap-dot" />
                  {editing && <span className="ap-label">{ap.name || ap.mac}</span>}
                  {!editing && heatLabels.get(ap.mac) && (
                    <span className="ap-label heat-label">{heatLabels.get(ap.mac)}</span>
                  )}
                </button>
              );
            })}
          {showPersons &&
            [...byAp.values()].flatMap((group) =>
              group.map((person, index) => {
                const angle = -Math.PI / 2 + (2 * Math.PI * index) / group.length;
                const dx = group.length > 1 ? Math.cos(angle) * FAN_RADIUS_PX : 0;
                const dy = group.length > 1 ? Math.sin(angle) * FAN_RADIUS_PX : 0;
                return (
                  <div
                    key={person.id}
                    className="person-marker"
                    style={{
                      left: `${(person.x ?? 0) * 100}%`,
                      top: `${(person.y ?? 0) * 100}%`,
                      transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`,
                    }}
                    title={`${person.name} near ${person.ap_name || person.ap_mac}`}
                    data-testid={`person-${person.id}`}
                  >
                    <span className="person-badge" style={{ background: colorOf(person.id) }}>
                      {initials(person.name)}
                    </span>
                    <span className="person-label">{person.name}</span>
                  </div>
                );
              }),
            )}
        </div>
      )}
    </div>
  );
}

export default FloorMap;
