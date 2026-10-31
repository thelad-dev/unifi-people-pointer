import { Overview } from '../api';
import { useApi } from '../useApi';

function Dashboard() {
  const { data, error } = useApi<Overview>('/overview');

  if (error && !data) return <div className="error">{error}</div>;
  if (!data) return <div className="loading">Loading overview...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Overview</h2>
        <p>Who is home, and at which access point</p>
      </div>

      {!data.last_update_success && (
        <div className="error">The last UniFi poll failed; values may be stale.</div>
      )}

      <div className="grid grid-3">
        <div className="stat-card">
          <h3>Persons home</h3>
          <div className="value">{data.persons_home} / {data.persons_total}</div>
        </div>
        <div className="stat-card">
          <h3>Devices online</h3>
          <div className="value">{data.devices_online} / {data.devices_total}</div>
        </div>
        <div className="stat-card">
          <h3>Unknown clients</h3>
          <div className="value">{data.unknown_clients}</div>
        </div>
        <div className="stat-card">
          <h3>Guest clients</h3>
          <div className="value">{data.guest_clients}</div>
        </div>
        <div className="stat-card">
          <h3>Access points</h3>
          <div className="value">{data.access_points}</div>
        </div>
      </div>

      <div className="card section">
        <h3>Presence</h3>
        {data.persons.length === 0 ? (
          <p className="muted">No persons configured yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Person</th>
                <th>State</th>
                <th>Access point</th>
                <th>Devices online</th>
              </tr>
            </thead>
            <tbody>
              {data.persons.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>
                    <span className={`badge ${p.state === 'home' ? 'badge-success' : 'badge-neutral'}`}>
                      {p.state === 'home' ? 'Home' : 'Away'}
                    </span>
                  </td>
                  <td>{p.ap_name || '-'}</td>
                  <td>{p.devices_online}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
