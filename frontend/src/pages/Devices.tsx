import { useState } from 'react';
import api, { DEVICE_TYPES, Device, errorText, Person } from '../api';
import { useApi } from '../useApi';

interface Form {
  name: string;
  mac: string;
  type: string;
  person: string;
  role: 'primary' | 'secondary';
}

const EMPTY: Form = { name: '', mac: '', type: 'smartphone', person: '', role: 'secondary' };

function Devices() {
  const { data: devices, error, reload } = useApi<Device[]>('/devices');
  const { data: persons } = useApi<Person[]>('/persons');
  const [editing, setEditing] = useState<Device | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);

  const personName = (id: string | null) =>
    (id && persons?.find((p) => p.id === id)?.name) || id || '-';

  const open = (device: Device | null) => {
    setEditing(device);
    setForm(
      device
        ? { name: device.name, mac: device.mac, type: device.type, person: device.person || '', role: 'secondary' }
        : EMPTY,
    );
    setFormError(null);
    setShowModal(true);
  };

  const remove = async (device: Device) => {
    if (!confirm(`Stop tracking ${device.name}?`)) return;
    try {
      await api.delete(`/devices/${encodeURIComponent(device.id)}`);
      reload();
    } catch (err) {
      alert(errorText(err));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) await api.put(`/devices/${encodeURIComponent(editing.id)}`, form);
      else await api.post('/devices', form);
      setShowModal(false);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  if (error && !devices) return <div className="error">{error}</div>;
  if (!devices) return <div className="loading">Loading devices...</div>;

  return (
    <div>
      <div className="page-header page-header-actions">
        <div>
          <h2>Devices</h2>
          <p>Tracked devices, their owner and current access point</p>
        </div>
        <button onClick={() => open(null)}>Add device</button>
      </div>

      {devices.length === 0 ? (
        <div className="empty-state">
          <h3>No devices yet</h3>
          <p>Add a device by MAC address or claim one from Unknown Clients.</p>
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Person</th>
                <th>Type</th>
                <th>MAC address</th>
                <th>Signal</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>
                    {d.online ? (
                      <span className="badge badge-success">{d.ap_name ? `AP: ${d.ap_name}` : 'Online'}</span>
                    ) : (
                      <span className="badge badge-neutral">Away</span>
                    )}
                  </td>
                  <td>{personName(d.person)}</td>
                  <td>{d.type}</td>
                  <td><code>{d.mac}</code></td>
                  <td>{d.signal != null ? `${d.signal} dBm` : '-'}</td>
                  <td>
                    <div className="button-row">
                      <button onClick={() => open(d)}>Edit</button>
                      <button className="button-danger" onClick={() => remove(d)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editing ? 'Edit device' : 'Add device'}</h3>
            {formError && <div className="error">{formError}</div>}
            <form onSubmit={submit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>MAC address</label>
                <input
                  type="text"
                  value={form.mac}
                  onChange={(e) => setForm({ ...form, mac: e.target.value })}
                  placeholder="aa:bb:cc:dd:ee:ff"
                  disabled={!!editing}
                  required
                />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  {DEVICE_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Person</label>
                <select value={form.person} onChange={(e) => setForm({ ...form, person: e.target.value })}>
                  <option value="">Nobody</option>
                  {(persons || []).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              {form.person && (
                <div className="form-group">
                  <label>Role</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value as Form['role'] })}
                  >
                    <option value="primary">Primary device</option>
                    <option value="secondary">Secondary device</option>
                  </select>
                </div>
              )}
              <div className="button-group">
                <button type="submit">Save</button>
                <button type="button" className="button-secondary" onClick={() => setShowModal(false)}>
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

export default Devices;
