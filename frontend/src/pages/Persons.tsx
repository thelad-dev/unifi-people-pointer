import { useState } from 'react';
import api, { errorText, Person } from '../api';
import { useApi } from '../useApi';

const EMPTY = { name: '', ha_person: '' };

function Persons() {
  const { data: persons, error, reload } = useApi<Person[]>('/persons');
  const [editing, setEditing] = useState<Person | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);

  const open = (person: Person | null) => {
    setEditing(person);
    setForm(person ? { name: person.name, ha_person: person.ha_person || '' } : EMPTY);
    setFormError(null);
    setShowModal(true);
  };

  const remove = async (person: Person) => {
    if (!confirm(`Delete ${person.name}? Their devices stay configured.`)) return;
    try {
      await api.delete(`/persons/${encodeURIComponent(person.id)}`);
      reload();
    } catch (err) {
      alert(errorText(err));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) await api.put(`/persons/${encodeURIComponent(editing.id)}`, form);
      else await api.post('/persons', form);
      setShowModal(false);
      reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  };

  if (error && !persons) return <div className="error">{error}</div>;
  if (!persons) return <div className="loading">Loading persons...</div>;

  return (
    <div>
      <div className="page-header page-header-actions">
        <div>
          <h2>Persons</h2>
          <p>People and their Home Assistant person link</p>
        </div>
        <button onClick={() => open(null)}>Add person</button>
      </div>

      {persons.length === 0 ? (
        <div className="empty-state">
          <h3>No persons yet</h3>
          <p>Add a person, then assign devices on the Devices page.</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {persons.map((person) => (
            <div key={person.id} className="card">
              <div className="card-row">
                <div>
                  <h3>{person.name}</h3>
                  <p className="muted small">{person.ha_person || 'no HA person linked'}</p>
                </div>
                <span className={`badge ${person.state === 'home' ? 'badge-success' : 'badge-neutral'}`}>
                  {person.state === 'home' ? 'Home' : 'Away'}
                </span>
              </div>
              <dl className="facts">
                <dt>Access point</dt>
                <dd>{person.ap_name || '-'}</dd>
                <dt>Devices</dt>
                <dd>{person.devices_online} of {person.device_ids.length} online</dd>
              </dl>
              <div className="button-row">
                <button onClick={() => open(person)}>Edit</button>
                <button className="button-danger" onClick={() => remove(person)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editing ? 'Edit person' : 'Add person'}</h3>
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
                <label>Home Assistant person (optional)</label>
                <input
                  type="text"
                  value={form.ha_person}
                  onChange={(e) => setForm({ ...form, ha_person: e.target.value })}
                  placeholder="person.jane"
                />
              </div>
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

export default Persons;
