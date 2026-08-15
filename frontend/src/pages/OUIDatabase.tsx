import { useState } from 'react';
import api from '../api';

interface OUIEntry {
  prefix: string;
  vendor: string;
}

interface LookupResult {
  mac: string;
  vendor: string | null;
}

function OUIDatabase() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<OUIEntry[]>([]);
  const [lookupMac, setLookupMac] = useState('');
  const [lookupResult, setLookupResult] = useState<LookupResult | null>(null);
  const [stats, setStats] = useState<{ totalEntries: number; vendors: number } | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      const res = await api.get(`/oui/search?query=${encodeURIComponent(searchQuery)}`);
      setSearchResults(res.data);
    } catch (err) {
      console.error('Failed to search OUI database:', err);
    }
  };

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupMac.trim()) return;

    try {
      const res = await api.get(`/oui/lookup/${lookupMac}`);
      setLookupResult(res.data);
    } catch (err) {
      console.error('Failed to lookup MAC:', err);
    }
  };

  const loadStats = async () => {
    try {
      const res = await api.get('/oui/stats');
      setStats(res.data);
    } catch (err) {
      console.error('Failed to load OUI stats:', err);
    }
  };

  useState(() => {
    loadStats();
  });

  return (
    <div>
      <div className="page-header">
        <h2>OUI Database</h2>
        <p>Look up device manufacturers by MAC address</p>
      </div>

      {stats && (
        <div className="grid grid-2" style={{ marginBottom: '2rem' }}>
          <div className="stat-card">
            <h3>Total Entries</h3>
            <div className="value">{stats.totalEntries}</div>
          </div>
          <div className="stat-card">
            <h3>Unique Vendors</h3>
            <div className="value">{stats.vendors}</div>
          </div>
        </div>
      )}

      <div className="grid grid-2">
        <div className="card">
          <h3>MAC Address Lookup</h3>
          <form onSubmit={handleLookup}>
            <div className="form-group">
              <label>MAC Address</label>
              <input
                type="text"
                value={lookupMac}
                onChange={(e) => setLookupMac(e.target.value)}
                placeholder="00:11:22:33:44:55"
              />
            </div>
            <button type="submit">Lookup</button>
          </form>

          {lookupResult && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'var(--background)', borderRadius: '4px' }}>
              <p><strong>MAC:</strong> <code>{lookupResult.mac}</code></p>
              <p><strong>Vendor:</strong> {lookupResult.vendor || 'Unknown'}</p>
            </div>
          )}
        </div>

        <div className="card">
          <h3>Search Database</h3>
          <form onSubmit={handleSearch}>
            <div className="form-group">
              <label>Search Query</label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Apple, Cisco, etc."
              />
            </div>
            <button type="submit">Search</button>
          </form>

          {searchResults.length > 0 && (
            <div style={{ marginTop: '1rem', maxHeight: '300px', overflowY: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Prefix</th>
                    <th>Vendor</th>
                  </tr>
                </thead>
                <tbody>
                  {searchResults.map((entry, idx) => (
                    <tr key={idx}>
                      <td><code>{entry.prefix}</code></td>
                      <td>{entry.vendor}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OUIDatabase;
