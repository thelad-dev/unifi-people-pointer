import { useEffect, useState } from 'react';
import api from '../api';

interface Stats {
  devices: number;
  persons: number;
  zones: number;
  unknownClients: number;
}

function Dashboard() {
  const [stats, setStats] = useState<Stats>({
    devices: 0,
    persons: 0,
    zones: 0,
    unknownClients: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
    
    // Connect to WebSocket for live updates
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = () => {
      fetchStats();
    };

    return () => {
      ws.close();
    };
  }, []);

  const fetchStats = async () => {
    try {
      const [devicesRes, personsRes, zonesRes, clientsRes] = await Promise.all([
        api.get('/devices'),
        api.get('/persons'),
        api.get('/zones'),
        api.get('/clients/unknown'),
      ]);

      setStats({
        devices: devicesRes.data.length,
        persons: personsRes.data.length,
        zones: zonesRes.data.length,
        unknownClients: clientsRes.data.length,
      });
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard stats');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Live overview of your UniFi People Pointer system</p>
      </div>

      <div className="grid grid-2">
        <div className="stat-card">
          <h3>Devices</h3>
          <div className="value">{stats.devices}</div>
        </div>

        <div className="stat-card">
          <h3>Persons</h3>
          <div className="value">{stats.persons}</div>
        </div>

        <div className="stat-card">
          <h3>Zones</h3>
          <div className="value">{stats.zones}</div>
        </div>

        <div className="stat-card">
          <h3>Unknown Clients</h3>
          <div className="value">{stats.unknownClients}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: '2rem' }}>
        <h3>System Status</h3>
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span>Backend API</span>
            <span className="badge badge-success">Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
