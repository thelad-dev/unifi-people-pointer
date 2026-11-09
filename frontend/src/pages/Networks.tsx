import { useState } from 'react';
import api, { DetectedNetwork, errorText, NetworkSettings } from '../api';
import { canonicalCidr, cidrError } from '../cidr';
import { useApi } from '../useApi';

const KIND_LABEL: Record<DetectedNetwork['kind'], string> = {
  unifi: 'UniFi network',
  observed: 'Seen in client addresses',
  custom: 'Added by hand',
};

function sameSet(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((key) => b.includes(key));
}

function clientsText(count: number): string {
  return count === 1 ? '1 client' : `${count} clients`;
}

function Networks() {
  const { data, error, reload } = useApi<NetworkSettings>('/networks');
  // Draft edits; null while the page mirrors what is saved.
  const [draft, setDraft] = useState<string[] | null>(null);
  const [draftUnassigned, setDraftUnassigned] = useState<boolean | null>(null);
  const [added, setAdded] = useState<string[]>([]);
  const [cidr, setCidr] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  if (error && !data) return <div className="error">{error}</div>;
  if (!data) return <div className="loading">Loading networks...</div>;

  const selected = draft ?? data.selected;
  const includeUnassigned = draftUnassigned ?? data.include_unassigned_clients;
  const dirty =
    !sameSet(selected, data.selected) || includeUnassigned !== data.include_unassigned_clients;

  const known = new Set(data.networks.map((n) => n.key));
  const rows: DetectedNetwork[] = [
    ...data.networks,
    ...added
      .filter((key) => !known.has(key))
      .map((key) => ({
        key,
        kind: 'custom' as const,
        name: key,
        vlan: null,
        subnets: [key],
        clients: -1,
        selected: true,
      })),
  ];

  const toggle = (key: string) => {
    setMessage(null);
    setDraft(selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };

  const addSubnet = (e: React.FormEvent) => {
    e.preventDefault();
    const problem = cidrError(cidr);
    setInputError(problem);
    if (problem) return;
    const key = canonicalCidr(cidr);
    setMessage(null);
    if (!known.has(key) && !added.includes(key)) setAdded([...added, key]);
    if (!selected.includes(key)) setDraft([...selected, key]);
    setCidr('');
  };

  const save = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.put('/networks', {
        networks: selected,
        include_unassigned_clients: includeUnassigned,
      });
      await reload();
      setDraft(null);
      setDraftUnassigned(null);
      setAdded([]);
      setMessage({ ok: true, text: 'Saved. All pages now use this selection.' });
    } catch (err) {
      setMessage({ ok: false, text: errorText(err) });
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setDraft(null);
    setDraftUnassigned(null);
    setAdded([]);
    setMessage(null);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Networks</h2>
        <p>Choose the networks People Pointer looks at</p>
      </div>

      <div className={`filter-status ${data.active ? 'filter-status-on' : ''}`}>
        {data.active
          ? 'Filter on: only clients in the selected networks count on every page, for entities and events.'
          : 'No filter: clients from every network are shown.'}
      </div>

      <div className="card">
        <h3>Detected networks</h3>
        {rows.length === 0 ? (
          <p className="muted">No networks seen yet. They appear after the next UniFi poll.</p>
        ) : (
          <ul className="network-list">
            {rows.map((n) => {
              const meta = [
                ...n.subnets.filter((s) => s !== n.name),
                n.vlan ? `VLAN ${n.vlan}` : null,
                KIND_LABEL[n.kind],
              ].filter(Boolean);
              return (
                <li key={n.key}>
                  <label className="network-row">
                    <input
                      type="checkbox"
                      checked={selected.includes(n.key)}
                      onChange={() => toggle(n.key)}
                    />
                    <span className="network-text">
                      <span className="network-name">{n.name}</span>
                      <span className="network-meta">{meta.join(' · ')}</span>
                    </span>
                    <span className="network-count">
                      {n.clients < 0 ? 'new' : clientsText(n.clients)}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}

        <form className="cidr-form" onSubmit={addSubnet} noValidate>
          <label htmlFor="cidr-input">Add a subnet</label>
          <div className="cidr-input-row">
            <input
              id="cidr-input"
              type="text"
              inputMode="text"
              autoComplete="off"
              spellCheck={false}
              placeholder="192.0.2.0/24 or 2001:db8::/64"
              value={cidr}
              aria-invalid={inputError ? true : undefined}
              onChange={(e) => {
                setCidr(e.target.value);
                setInputError(null);
              }}
            />
            <button type="submit" className="button-secondary">Add</button>
          </div>
          {inputError && <p className="field-error">{inputError}</p>}
        </form>
      </div>

      <div className="card">
        <ul className="network-list">
          <li>
            <label className="network-row">
              <input
                type="checkbox"
                checked={includeUnassigned}
                onChange={() => {
                  setMessage(null);
                  setDraftUnassigned(!includeUnassigned);
                }}
              />
              <span className="network-text">
                <span className="network-name">Show clients without a network</span>
                <span className="network-meta">
                  Clients that report neither an IP address nor a UniFi network. Applies while
                  networks are selected.
                </span>
              </span>
              <span className="network-count">{clientsText(data.unassigned_clients)}</span>
            </label>
          </li>
        </ul>
      </div>

      <div className="network-actions">
        <button onClick={save} disabled={!dirty || saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        {dirty && (
          <button className="button-secondary" onClick={discard} disabled={saving}>
            Discard changes
          </button>
        )}
        {selected.length > 0 && (
          <button
            className="button-secondary"
            onClick={() => {
              setMessage(null);
              setDraft([]);
            }}
            disabled={saving}
          >
            Clear selection
          </button>
        )}
        {message && (
          <span className={message.ok ? 'save-ok' : 'field-error'} role="status">
            {message.text}
          </span>
        )}
      </div>
    </div>
  );
}

export default Networks;
