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
    // Short-lived panel tokens expire; ask the panel for a fresh one.
    panelToken = null;
    requestPanelToken();
    listeners.forEach((fn) => fn());
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
  persons: Person[];
}

export const DEVICE_TYPES = ['smartphone', 'tablet', 'laptop', 'watch', 'wearable', 'other'];

export default api;
