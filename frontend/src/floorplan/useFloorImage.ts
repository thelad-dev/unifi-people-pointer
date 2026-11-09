import { useEffect, useState } from 'react';
import api, { errorText } from '../api';

// Floor images need the access token, which an <img src> cannot send, so they
// are fetched as blobs. URLs change with every upload; keep each one once.
const cache = new Map<string, Promise<string>>();

function load(url: string): Promise<string> {
  let pending = cache.get(url);
  if (!pending) {
    pending = api
      .get<Blob>(url.replace(/^\/api/, ''), { responseType: 'blob' })
      .then((res) => URL.createObjectURL(res.data));
    pending.catch(() => cache.delete(url));
    cache.set(url, pending);
  }
  return pending;
}

export function useFloorImage(url: string | null) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setSrc(null);
    setError(null);
    if (!url) return;
    load(url).then(
      (value) => active && setSrc(value),
      (err) => active && setError(errorText(err)),
    );
    return () => {
      active = false;
    };
  }, [url]);

  return { src, error };
}
