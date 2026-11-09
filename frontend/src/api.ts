import axios from 'axios';

// Token handoff: inside the Home Assistant panel the parent window posts the
// current access token; opened directly, a long-lived token is stored locally.
const STORAGE_KEY = 'upp-ha-token';
const AUTH_REQUEST = 'upp-auth-request';
const AUTH_MESSAGE = 'upp-auth';

let panelToken: string | null = null;
const listeners = new Set<() => void>();

export const embedded = window.parent !== window;

function storedToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function currentToken(): string | null {
  return panelToken || storedToken();
}

export function saveToken(token: string | null) {
  try {
    if (token) localStorage.setItem(STORAGE_KEY, token);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage unavailable (private mode): keep the token for this page only.
    panelToken = token;
  }
  listeners.forEach((fn) => fn());
}

export function onTokenChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function requestPanelToken() {
  if (embedded) window.parent.postMessage({ type: AUTH_REQUEST }, '*');
}

window.addEventListener('message', (event: MessageEvent) => {
  if (event.source !== window.parent || event.data?.type !== AUTH_MESSAGE) return;
  if (typeof event.data.token === 'string' && event.data.token !== panelToken) {
    panelToken = event.data.token;
    listeners.forEach((fn) => fn());
  }
});

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = currentToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(undefined, (error) => {
  if (error?.response?.status === 401) {
    if (embedded) {
      // Short-lived panel tokens expire; the panel answers with a fresh one
      // and the next refresh succeeds without leaving the page.
      requestPanelToken();
    } else {
      saveToken(null);
    }
  }
  return Promise.reject(error);
});

export function errorText(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data;
    if (typeof data === 'string' && data) return data;
    if (data && typeof data.error === 'string') return data.error;
    return err.message;
  }
  return String(err);
}

export interface Person {
  id: string;
  name: string;
  ha_person: string | null;
  device_ids: string[];
  state: 'home' | 'away';
  devices_online: number;
  ap_name: string | null;
}

export interface Device {
  id: string;
  name: string;
  mac: string;
  type: string;
  track: boolean;
  person: string | null;
  online: boolean;
  ip: string | null;
  hostname: string | null;
  signal: number | null;
  ap_mac: string | null;
  ap_name: string | null;
  last_seen: string | null;
  // Online only in a network outside the network filter.
  filtered: boolean;
}

export interface UnknownClient {
  mac: string;
  hostname: string | null;
  ip: string | null;
  signal: number | null;
  ap_mac: string | null;
  ap_name: string | null;
  last_seen: string | null;
}

export interface AccessPoint {
  mac: string;
  name: string | null;
  clients: number;
}

export interface Overview {
  persons_home: number;
  persons_total: number;
  devices_online: number;
  devices_total: number;
  unknown_clients: number;
  guest_clients: number;
  access_points: number;
  last_update_success: boolean;
  // Selected networks; empty when every network is shown.
  network_filter: string[];
  persons: Person[];
}

export interface DetectedNetwork {
  // CIDR or "network:<UniFi network id>"; also the value stored when selected.
  key: string;
  kind: 'unifi' | 'observed' | 'custom';
  name: string;
  vlan: number | null;
  subnets: string[];
  clients: number;
  selected: boolean;
}

export interface NetworkSettings {
  selected: string[];
  include_unassigned_clients: boolean;
  active: boolean;
  networks: DetectedNetwork[];
  unassigned_clients: number;
}

export interface Floor {
  id: string;
  name: string;
  level: number;
  width: number;
  height: number;
  width_m: number | null;
  image_url: string;
}

// Position on a floor as fractions of the image width and height (0..1).
export interface MapPosition {
  floor: string | null;
  x: number | null;
  y: number | null;
}

export interface MapAccessPoint extends MapPosition {
  mac: string;
  name: string | null;
  clients: number;
}

export interface MapPerson extends MapPosition {
  id: string;
  name: string;
  ap_mac: string;
  ap_name: string | null;
  signal: number | null;
  radius_m: number;
}

export interface FloorPlanPrivacy {
  locate_persons: boolean;
  persons: string[];
}

export interface FloorPlanData {
  floors: Floor[];
  aps: MapAccessPoint[];
  persons: MapPerson[];
  privacy: FloorPlanPrivacy;
}

export type UsagePeriod = 'now' | '1h' | '24h' | '7d';

export interface ApUsage extends MapPosition {
  mac: string;
  name: string | null;
  clients: number;
  clients_max: number;
  bytes: number | null;
}

export interface UsageData {
  period: UsagePeriod;
  bytes_unit: 'B/s' | 'B';
  has_bytes: boolean;
  samples: number;
  since: string | null;
  aps: ApUsage[];
}

export interface InnerSpaceImport {
  floors_created: number;
  floors_updated: number;
  aps_placed: number;
  skipped_aps: string[];
  warnings: string[];
}

// Multipart upload: let the browser set the boundary.
export function postForm<T>(method: 'post' | 'put', path: string, form: FormData) {
  return api.request<T>({
    method,
    url: path,
    data: form,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export const DEVICE_TYPES = ['smartphone', 'tablet', 'laptop', 'watch', 'wearable', 'other'];

export default api;
