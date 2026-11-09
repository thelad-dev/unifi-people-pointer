import { useState } from 'react';
import api, { errorText, FloorPlanData, MapPerson, Person, UsageData, UsagePeriod } from '../api';
import { useApi } from '../useApi';
import EditPanel from '../floorplan/EditPanel';
import FloorMap from '../floorplan/FloorMap';
import { AddFloorDialog, InnerSpaceDialog } from '../floorplan/FloorDialogs';
import { HeatMetric, HeatmapPanel, PERIODS, heatSpots } from '../floorplan/heatmap';
import { personColors, readStored, writeStored } from '../floorplan/util';

const FLOOR_KEY = 'upp-floor';

interface PersonListProps {
  title: string;
  persons: MapPerson[];
  note: (p: MapPerson) => string;
  colorOf: (id: string) => string;
}

function PersonList({ title, persons, note, colorOf }: PersonListProps) {
  if (persons.length === 0) return null;
  return (
    <>
      <h4>{title}</h4>
      <ul className="person-list">
        {persons.map((person) => (
          <li key={person.id}>
            <span className="person-dot" style={{ background: colorOf(person.id) }} />
            <span>
              {person.name}
              <span className="muted small"> {note(person)}</span>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function FloorPlan() {
  const { data, error, reload } = useApi<FloorPlanData>('/floorplan');
  const { data: persons } = useApi<Person[]>('/persons');
  const [floorId, setFloorId] = useState<string | null>(readStored(FLOOR_KEY));
  const [editing, setEditing] = useState(false);
  const [showAps, setShowAps] = useState(true);
  const [showPersons, setShowPersons] = useState(true);
  const [placing, setPlacing] = useState<string | null>(null);
  const [dialog, setDialog] = useState<'add' | 'import' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showHeat, setShowHeat] = useState(false);
  const [period, setPeriod] = useState<UsagePeriod>('now');
  const [metric, setMetric] = useState<HeatMetric>('clients');
  const heatOn = showHeat && !editing;
  const { data: usageData, error: usageError } = useApi<UsageData>(
    heatOn ? `/floorplan/usage?period=${period}` : null,
  );
  // Until the selected period has loaded, show nothing rather than old values.
  const usage = usageData && usageData.period === period ? usageData : null;
  const heatMetric: HeatMetric = metric === 'bytes' && usage && !usage.has_bytes ? 'clients' : metric;

  if (error && !data) return <div className="error">{error}</div>;
  if (!data) return <div className="loading">Loading floor plan...</div>;

  const floor = data.floors.find((f) => f.id === floorId) || data.floors[0] || null;
  const selectFloor = (id: string) => {
    setFloorId(id);
    setPlacing(null);
    writeStored(FLOOR_KEY, id);
  };

  const place = async (mac: string, x: number, y: number) => {
    if (!floor) return;
    setPlacing(null);
    try {
      await api.put(`/floorplan/aps/${encodeURIComponent(mac)}`, { floor: floor.id, x, y });
      setActionError(null);
    } catch (err) {
      setActionError(errorText(err));
    }
    reload();
  };

  const floorName = (id: string | null) => data.floors.find((f) => f.id === id)?.name || '';
  const onFloor = floor ? data.persons.filter((p) => p.floor === floor.id) : [];
  const otherFloors = data.persons.filter((p) => p.floor && p.floor !== floor?.id);
  const unplaced = data.persons.filter((p) => !p.floor);

  const dialogs = (
    <>
      {dialog === 'add' && (
        <AddFloorDialog
          onClose={() => setDialog(null)}
          onAdded={(added) => {
            setDialog(null);
            selectFloor(added.id);
            setEditing(true);
            reload();
          }}
        />
      )}
      {dialog === 'import' && <InnerSpaceDialog onClose={() => setDialog(null)} onImported={reload} />}
    </>
  );

  if (!floor) {
    return (
      <div>
        <div className="page-header">
          <h2>Floor plan</h2>
          <p>Where people are, roughly: at the access point their device uses</p>
        </div>
        <div className="card empty-floorplan">
          <h3>No floor plans yet</h3>
          <p className="muted">
            Upload one image per floor and place the access points on it, or import floor plans and access point
            positions once from UniFi InnerSpace.
          </p>
          <div className="button-row">
            <button onClick={() => setDialog('add')}>Upload floor plan</button>
            <button className="button-secondary" onClick={() => setDialog('import')}>
              Import from UniFi InnerSpace
            </button>
          </div>
        </div>
        {dialogs}
      </div>
    );
  }

  const apsHere = data.aps.filter((ap) => ap.floor === floor.id);
  const colorOf = personColors((persons || []).map((p) => p.id));

  return (
    <div className="floorplan-page">
      <div className="floorplan-toolbar">
        <h2>Floor plan</h2>
        <div className="segmented" role="group" aria-label="Mode">
          <button className={!editing ? 'active' : undefined} onClick={() => { setEditing(false); setPlacing(null); }}>
            View
          </button>
          <button className={editing ? 'active' : undefined} onClick={() => setEditing(true)}>
            Edit
          </button>
        </div>
      </div>

      <div className="floorplan-controls">
        <div className="floor-tabs" role="tablist" aria-label="Floors">
          {data.floors.map((f) => (
            <button
              key={f.id}
              role="tab"
              aria-selected={f.id === floor.id}
              className={f.id === floor.id ? 'active' : undefined}
              onClick={() => selectFloor(f.id)}
            >
              {f.name}
              {data.persons.some((p) => p.floor === f.id) && <span className="floor-tab-dot" aria-hidden="true" />}
            </button>
          ))}
          {editing && (
            <button className="floor-tab-add" onClick={() => setDialog('add')} aria-label="Add floor">
              + Floor
            </button>
          )}
        </div>
        {!editing && (
          <div className="layer-toggles">
            <label className="check">
              <input type="checkbox" checked={showPersons} onChange={(e) => setShowPersons(e.target.checked)} />
              Persons
            </label>
            <label className="check">
              <input type="checkbox" checked={showHeat} onChange={(e) => setShowHeat(e.target.checked)} />
              Heatmap
            </label>
            <label className="check">
              <input type="checkbox" checked={showAps} onChange={(e) => setShowAps(e.target.checked)} />
              Access points
            </label>
          </div>
        )}
      </div>

      {heatOn && (
        <div className="heat-controls">
          <div className="segmented" role="group" aria-label="Period">
            {PERIODS.map((p) => (
              <button key={p.id} className={p.id === period ? 'active' : undefined} onClick={() => setPeriod(p.id)}>
                {p.label}
              </button>
            ))}
          </div>
          <div className="segmented" role="group" aria-label="Measure">
            <button className={heatMetric === 'clients' ? 'active' : undefined} onClick={() => setMetric('clients')}>
              Clients
            </button>
            <button
              className={heatMetric === 'bytes' ? 'active' : undefined}
              onClick={() => setMetric('bytes')}
              disabled={!!usage && !usage.has_bytes}
              title={usage && !usage.has_bytes ? 'UniFi reports no client data rates here' : undefined}
            >
              Data
            </button>
          </div>
        </div>
      )}

      {actionError && <div className="error">{actionError}</div>}

      <div className="floorplan-layout">
        <FloorMap
          floor={floor}
          aps={apsHere}
          persons={onFloor}
          showAps={showAps}
          showPersons={showPersons && !editing}
          editing={editing}
          placing={placing}
          onPlace={place}
          colorOf={colorOf}
          heat={heatOn && usage ? heatSpots(usage, heatMetric, floor) : null}
        />
        <aside className="floorplan-side">
          {editing ? (
            <>
              <EditPanel
                data={data}
                floor={floor}
                persons={persons || []}
                placing={placing}
                setPlacing={setPlacing}
                reload={reload}
                onDeleted={() => {
                  setFloorId(null);
                  reload();
                }}
              />
              <div className="card side-card">
                <h3>UniFi InnerSpace</h3>
                <p className="muted small">Take over floor plans and access point positions once.</p>
                <button className="button-secondary" onClick={() => setDialog('import')}>
                  Import from InnerSpace
                </button>
              </div>
            </>
          ) : (
            <>
              {heatOn && (
                <HeatmapPanel usage={usage} metric={heatMetric} floors={data.floors} error={usageError} />
              )}
              {showPersons && (
                <div className="card side-card">
                  <h3>Persons</h3>
                  {!data.privacy.locate_persons ? (
                    <p className="muted small">Locating persons is off. Switch it on under Edit, Privacy.</p>
                  ) : data.persons.length === 0 ? (
                    <p className="muted small">No released person is at home right now.</p>
                  ) : (
                    <>
                      <PersonList
                        title={`On ${floor.name}`}
                        persons={onFloor}
                        colorOf={colorOf}
                        note={(p) => `near ${p.ap_name || p.ap_mac}, about ${Math.round(p.radius_m)} m`}
                      />
                      <PersonList
                        title="Other floors"
                        persons={otherFloors}
                        colorOf={colorOf}
                        note={(p) => `on ${floorName(p.floor)}`}
                      />
                      <PersonList
                        title="Not on the plan"
                        persons={unplaced}
                        colorOf={colorOf}
                        note={(p) => `at ${p.ap_name || p.ap_mac}, access point not placed`}
                      />
                    </>
                  )}
                  <p className="legend muted small">
                    <span className="legend-circle" /> The circle is the rough range around the access point,
                    estimated from signal strength. UniFi reports only the one access point a device uses.
                  </p>
                </div>
              )}
            </>
          )}
        </aside>
      </div>
      {dialogs}
    </div>
  );
}

export default FloorPlan;
