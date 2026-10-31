import { useState } from 'react';
import api, { errorText, Person, UnknownClient } from '../api';
import { useApi } from '../useApi';

interface Form {
  person: string;
  name: string;
  role: 'primary' | 'secondary';
}

function UnknownClients() {
  const { data: clients, error, reload } = useApi<UnknownClient[]>('/clients/unknown');
  const { data: persons } = useApi<Person[]>('/persons');
  const [selected, setSelected] = useState<UnknownClient | null>(null);
  const [form, setForm] = useState<Form>({ person: '', name: '', role: 'secondary' });
  const [formError, setFormError] = useState<string | null>(null);

  const open = (client: UnknownClient) => {
    setSelected(client);
    setForm({ person: '', name: client.hostname || '', role: 'secondary' });
    setFormError(null);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;
    try {
      await api.post(`/clients/${encodeURIComponent(selected.mac)}/claim`, form);
      setSelected(null);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  if (error && !clients) return <div className="error">{error}</div>;
  if (!clients) return <div className="loading">Loading unknown clients...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Unknown Clients</h2>
        <p>Wireless clients that match no configured device; claim one to assign it to a person</p>
      </div>

      {clients.length === 0 ? (
        <div className="empty-state">
          <h3>No unknown clients</h3>
          <p>Every wireless client matches a configured device.</p>
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Hostname</th>
                <th>MAC address</th>
                <th>IP</th>
                <th>Access point</th>
                <th>Signal</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.mac}>
                  <td>{c.hostname || <span className="muted">-</span>}</td>
                  <td><code>{c.mac}</code></td>
                  <td>{c.ip || '-'}</td>
                  <td>{c.ap_name || c.ap_mac || '-'}</td>
                  <td>{c.signal != null ? `${c.signal} dBm` : '-'}</td>
                  <td>
                    <button onClick={() => open(c)} disabled={!persons?.length}>Claim</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Claim client</h3>
            <p className="muted">MAC <code>{selected.mac}</code></p>
            {formError && <div className="error">{formError}</div>}
            <form onSubmit={submit}>
              <div className="form-group">
                <label>Person</label>
                <select value={form.person} onChange={(e) => setForm({ ...form, person: e.target.value })} required>
                  <option value="">Select a person</option>
                  {(persons || []).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Device name</label>
                <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Form['role'] })}>
                  <option value="primary">Primary device</option>
                  <option value="secondary">Secondary device</option>
                </select>
              </div>
              <div className="button-group">
                <button type="submit">Claim</button>
                <button type="button" className="button-secondary" onClick={() => setSelected(null)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default UnknownClients;
