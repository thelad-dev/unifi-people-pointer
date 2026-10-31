import { AccessPoint } from '../api';
import { useApi } from '../useApi';

function AccessPoints() {
  const { data, error } = useApi<AccessPoint[]>('/access-points');

  if (error && !data) return <div className="error">{error}</div>;
  if (!data) return <div className="loading">Loading access points...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Access Points</h2>
        <p>Names come from the UniFi device list; entities show them as "Name AP: Access point"</p>
      </div>
      {data.length === 0 ? (
        <div className="empty-state">
          <h3>No access points known yet</h3>
          <p>They appear after the next UniFi poll.</p>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>MAC address</th>
                <th>Wireless clients</th>
              </tr>
            </thead>
            <tbody>
              {data.map((ap) => (
                <tr key={ap.mac}>
                  <td>{ap.name || <span className="muted">unnamed</span>}</td>
                  <td><code>{ap.mac}</code></td>
                  <td>{ap.clients}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AccessPoints;
