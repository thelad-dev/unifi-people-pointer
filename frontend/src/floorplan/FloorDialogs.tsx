import { useState } from 'react';
import api, { errorText, Floor, InnerSpaceImport, postForm } from '../api';

interface AddFloorProps {
  onClose: () => void;
  onAdded: (floor: Floor) => void;
}

export function AddFloorDialog({ onClose, onAdded }: AddFloorProps) {
  const [name, setName] = useState('');
  const [level, setLevel] = useState('0');
  const [widthM, setWidthM] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append('name', name);
    form.append('level', level);
    form.append('width_m', widthM);
    form.append('image', file);
    setBusy(true);
    try {
      const res = await postForm<Floor>('post', '/floorplan/floors', form);
      onAdded(res.data);
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Add floor">
        <h3>Add floor</h3>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <div className="form-group">
            <label htmlFor="floor-name">Name</label>
            <input id="floor-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="floor-level">Level</label>
              <input id="floor-level" type="number" step="1" value={level} onChange={(e) => setLevel(e.target.value)} />
            </div>
            <div className="form-group">
              <label htmlFor="floor-width">Real width in meters (optional)</label>
              <input
                id="floor-width"
                type="number"
                step="0.1"
                min="1"
                value={widthM}
                onChange={(e) => setWidthM(e.target.value)}
                placeholder="e.g. 12"
              />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="floor-image">Floor plan image (PNG, JPEG or WebP)</label>
            <input
              id="floor-image"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
          </div>
          <p className="muted small">
            Level orders the floors (for example -1 basement, 0 ground floor). The real width sizes the
            uncertainty circles; without it the plan counts as 15 m wide.
          </p>
          <div className="button-group">
            <button type="submit" disabled={busy || !file}>
              {busy ? 'Uploading...' : 'Add floor'}
            </button>
            <button type="button" className="button-secondary" onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface ImportProps {
  onClose: () => void;
  onImported: () => void;
}

export function InnerSpaceDialog({ onClose, onImported }: ImportProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InnerSpaceImport | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<InnerSpaceImport>('/floorplan/import/innerspace', { username, password });
      setResult(res.data);
      onImported();
    } catch (err) {
      setError(errorText(err));
    } finally {
      // The password is only needed for this one request.
      setPassword('');
      setBusy(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Import from UniFi InnerSpace">
        <h3>Import from UniFi InnerSpace</h3>
        {result ? (
          <>
            <p>
              {result.floors_created} floor(s) added, {result.floors_updated} updated, {result.aps_placed} access
              point(s) placed.
            </p>
            {[...result.warnings, ...result.skipped_aps.map((ap) => `Not placed: ${ap}`)].length > 0 && (
              <ul className="notes">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
                {result.skipped_aps.map((ap) => (
                  <li key={ap}>Not placed: {ap}</li>
                ))}
              </ul>
            )}
            <div className="button-group">
              <button type="button" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="muted small">
              Signs in to UniFi OS once to read the floor plans and access point positions, then signs out.
              Use a local UniFi OS account with the Admin role for InnerSpace and without two-factor sign-in.
              The password is not stored. Floors with the same name are replaced together with the positions
              of their access points; other floors stay as they are.
            </p>
            {error && <div className="error">{error}</div>}
            <form onSubmit={submit}>
              <div className="form-group">
                <label htmlFor="is-user">UniFi OS user name</label>
                <input
                  id="is-user"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="off"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="is-password">Password</label>
                <input
                  id="is-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="off"
                  required
                />
              </div>
              <div className="button-group">
                <button type="submit" disabled={busy}>
                  {busy ? 'Importing...' : 'Import'}
                </button>
                <button type="button" className="button-secondary" onClick={onClose}>
                  Cancel
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
