import { useCallback, useEffect, useState } from 'react';
import api, { errorText } from './api';

const REFRESH_MS = 15000;

// GET a resource, refresh it periodically, expose a manual reload.
// A null path fetches nothing (for data a page only sometimes needs).
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (path === null) return;
    try {
      const res = await api.get<T>(path);
      setData(res.data);
      setError(null);
    } catch (err) {
      setError(errorText(err));
    }
  }, [path]);

  useEffect(() => {
    if (path === null) return;
    reload();
    const timer = window.setInterval(reload, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  return { data, error, reload };
}
