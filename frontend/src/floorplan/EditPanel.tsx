import { useEffect, useState } from 'react';
import api, { errorText, Floor, FloorPlanData, MapAccessPoint, Person, postForm } from '../api';

interface Props {
  data: FloorPlanData;
  floor: Floor;
  persons: Person[];
  placing: string | null;
  setPlacing: (mac: string | null) => void;
  reload: () => void;
  onDeleted: () => void;
}

function apLabel(ap: MapAccessPoint) {
  return ap.name || ap.mac;
}

function FloorSettings({ floor, reload, onDeleted }: Pick<Props, 'floor' | 'reload' | 'onDeleted'>) {
  const [name, setName] = useState(floor.name);
  const [level, setLevel] = useState(String(floor.level));
  const [widthM, setWidthM] = useState(floor.width_m == null ? '' : String(floor.width_m));
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);

  useEffect(() => {
    setName(floor.name);
    setLevel(String(floor.level));
    setWidthM(floor.width_m == null ? '' : String(floor.width_m));
    setMessage(null);
  }, [floor.id, floor.name, floor.level, floor.width_m]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.put(`/floorplan/floors/${encodeURIComponent(floor.id)}`, {
        name,
        level,
        width_m: widthM === '' ? null : widthM,
      });
      setMessage({ error: false, text: 'Saved' });
      reload();
    } catch (err) {
      setMessage({ error: true, text: errorText(err) });
    }
  };

  const replace = async (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append('image', file);
    try {
      await postForm('put', `/floorplan/floors/${encodeURIComponent(floor.id)}/image`, form);
      setMessage({ error: false, text: 'Image replaced; access points keep their places' });
      reload();
    } catch (err) {
      setMessage({ error: true, text: errorText(err) });
    }
  };

  const remove = async () => {
    if (!confirm(`Delete floor ${floor.name}? Its image and access point positions are removed.`)) return;
    try {
      await api.delete(`/floorplan/floors/${encodeURIComponent(floor.id)}`);
      onDeleted();
    } catch (err) {
      setMessage({ error: true, text: errorText(err) });
    }
  };

  return (
    <div className="card side-card">
      <h3>Floor</h3>
      {message && <div className={message.error ? 'error' : 'notice'}>{message.text}</div>}
      <form onSubmit={save}>
        <div className="form-group">
          <label htmlFor="edit-floor-name">Name</label>
          <input id="edit-floor-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} required />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="edit-floor-level">Level</label>
            <input id="edit-floor-level" type="number" step="1" value={level} onChange={(e) => setLevel(e.target.value)} />
          </div>
          <div className="form-group">
            <label htmlFor="edit-floor-width">Width (m)</label>
            <input
              id="edit-floor-width"
              type="number"
              step="0.1"
              min="1"
              value={widthM}
              onChange={(e) => setWidthM(e.target.value)}
              placeholder="15"
            />
          </div>
        </div>
        <div className="button-row">
          <button type="submit" className="button-small">
            Save
          </button>
          <label className="button-secondary button-small file-button">
            Replace image
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => {
                replace(e.target.files?.[0]);
                e.target.value = '';
              }}
            />
          </label>
          <button type="button" className="button-danger button-small" onClick={remove}>
            Delete
          </button>
        </div>
      </form>
    </div>
  );
}

function ApPlacement({ data, floor, placing, setPlacing, reload }: Omit<Props, 'persons' | 'onDeleted'>) {
  const [error, setError] = useState<string | null>(null);
  const here = data.aps.filter((ap) => ap.floor === floor.id);
  const elsewhere = data.aps.filter((ap) => ap.floor && ap.floor !== floor.id);
  const unplaced = data.aps.filter((ap) => !ap.floor);
  const floorName = (id: string | null) => data.floors.find((f) => f.id === id)?.name || id;

  const unplace = async (ap: MapAccessPoint) => {
    try {
      await api.delete(`/floorplan/aps/${encodeURIComponent(ap.mac)}`);
      setError(null);
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  };

  const row = (ap: MapAccessPoint, action: React.ReactNode, note?: string) => (
    <li key={ap.mac} className={placing === ap.mac ? 'ap-row ap-row-active' : 'ap-row'}>
      <span className="ap-row-name">
        {apLabel(ap)}
        {note && <span className="muted small"> {note}</span>}
      </span>
      {action}
    </li>
  );

  const placeButton = (ap: MapAccessPoint, label: string) =>
    placing === ap.mac ? (
      <button type="button" className="button-secondary button-small" onClick={() => setPlacing(null)}>
        Cancel
      </button>
    ) : (
      <button type="button" className="button-small" onClick={() => setPlacing(ap.mac)}>
        {label}
      </button>
    );

  return (
    <div className="card side-card">
      <h3>Access points</h3>
      <p className="muted small">
        {placing
          ? 'Click the spot on the plan where this access point hangs.'
          : 'Choose Place, then click the spot on the plan. Drag markers to move them; arrow keys move a focused marker.'}
      </p>
      {error && <div className="error">{error}</div>}
      {data.aps.length === 0 && <p className="muted">No access points known yet.</p>}
      <ul className="ap-list">
        {here.map((ap) =>
          row(
            ap,
            <button type="button" className="button-secondary button-small" onClick={() => unplace(ap)}>
              Remove
            </button>,
          ),
        )}
        {unplaced.map((ap) => row(ap, placeButton(ap, 'Place'), 'not placed'))}
        {elsewhere.map((ap) => row(ap, placeButton(ap, 'Move here'), `on ${floorName(ap.floor)}`))}
      </ul>
    </div>
  );
}

function PrivacySettings({ data, persons, reload }: Pick<Props, 'data' | 'persons' | 'reload'>) {
  const [enabled, setEnabled] = useState(data.privacy.locate_persons);
  const [released, setReleased] = useState<string[]>(data.privacy.persons);
  const [message, setMessage] = useState<{ error: boolean; text: string } | null>(null);

  useEffect(() => {
    setEnabled(data.privacy.locate_persons);
    setReleased(data.privacy.persons);
  }, [data.privacy.locate_persons, data.privacy.persons.join(',')]);

  const save = async (nextEnabled: boolean, nextReleased: string[]) => {
    setEnabled(nextEnabled);
    setReleased(nextReleased);
    try {
      await api.put('/floorplan/privacy', { locate_persons: nextEnabled, persons: nextReleased });
      setMessage(null);
      reload();
    } catch (err) {
      setMessage({ error: true, text: errorText(err) });
    }
  };

  const toggle = (id: string) =>
    save(enabled, released.includes(id) ? released.filter((p) => p !== id) : [...released, id]);

  return (
    <div className="card side-card">
      <h3>Privacy</h3>
      <p className="muted small">
        Persons appear on the plan only while locating is on and they are released here. Nothing about their
        position is kept as history.
      </p>
      {message && <div className="error">{message.text}</div>}
      <label className="check">
        <input type="checkbox" checked={enabled} onChange={(e) => save(e.target.checked, released)} />
        Show persons on the floor plan
      </label>
      <ul className="check-list">
        {persons.map((person) => (
          <li key={person.id}>
            <label className="check">
              <input
                type="checkbox"
                checked={released.includes(person.id)}
                disabled={!enabled}
                onChange={() => toggle(person.id)}
              />
              {person.name}
            </label>
          </li>
        ))}
      </ul>
      {persons.length === 0 && <p className="muted small">No persons configured.</p>}
    </div>
  );
}

function EditPanel(props: Props) {
  return (
    <>
      <FloorSettings floor={props.floor} reload={props.reload} onDeleted={props.onDeleted} />
      <ApPlacement
        data={props.data}
        floor={props.floor}
        placing={props.placing}
        setPlacing={props.setPlacing}
        reload={props.reload}
      />
      <PrivacySettings data={props.data} persons={props.persons} reload={props.reload} />
    </>
  );
}

export default EditPanel;
