import { useEffect, useState } from 'react';
import api from '../api';

interface Client {
  mac: string;
  hostname?: string;
  vendor?: string;
  lastSeen: string;
}

interface Person {
  id: string;
  name: string;
}

function UnknownClients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [showAssociateModal, setShowAssociateModal] = useState(false);
  const [selectedPersonId, setSelectedPersonId] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [clientsRes, personsRes] = await Promise.all([
        api.get('/clients/unknown'),
        api.get('/persons'),
      ]);
      setClients(clientsRes.data);
      setPersons(personsRes.data);
    } catch (err) {
      console.error('Failed to load unknown clients:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleIgnore = async (mac: string) => {
    try {
      await api.post(`/clients/${mac}/ignore`);
      fetchData();
    } catch (err) {
      console.error('Failed to ignore client:', err);
    }
  };

  const handleAssociate = (client: Client) => {
    setSelectedClient(client);
    setSelectedPersonId('');
    setShowAssociateModal(true);
  };

  const handleAssociateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClient) return;

    try {
      await api.post(`/clients/${selectedClient.mac}/associate`, {
        personId: selectedPersonId,
      });
      setShowAssociateModal(false);
      fetchData();
    } catch (err) {
      console.error('Failed to associate client:', err);
    }
  };

  const lookupOui = async (mac: string) => {
    try {
      const res = await api.get(`/oui/lookup/${mac}`);
      return res.data.vendor || 'Unknown';
    } catch (err) {
      return 'Unknown';
    }
  };

  if (loading) {
    return <div className="loading">Loading unknown clients...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>Unknown Clients</h2>
        <p>Review and classify unknown devices on your network</p>
      </div>

      {clients.length === 0 ? (
        <div className="empty-state">
          <h3>No unknown clients</h3>
          <p>All detected clients have been classified</p>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>MAC Address</th>
                <th>Hostname</th>
                <th>Vendor</th>
                <th>Last Seen</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map(client => (
                <tr key={client.mac}>
                  <td><code>{client.mac}</code></td>
                  <td>{client.hostname || '-'}</td>
                  <td>{client.vendor || 'Unknown'}</td>
                  <td>{new Date(client.lastSeen).toLocaleString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button onClick={() => handleAssociate(client)}>Associate</button>
                      <button className="button-secondary" onClick={() => handleIgnore(client.mac)}>
                        Ignore
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAssociateModal && selectedClient && (
        <div className="modal-overlay" onClick={() => setShowAssociateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Associate Client</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              MAC: <code>{selectedClient.mac}</code>
            </p>
            <form onSubmit={handleAssociateSubmit}>
              <div className="form-group">
                <label>Assign to Person</label>
                <select
                  value={selectedPersonId}
                  onChange={(e) => setSelectedPersonId(e.target.value)}
                  required
                >
                  <option value="">Select a person</option>
                  {persons.map(person => (
                    <option key={person.id} value={person.id}>{person.name}</option>
                  ))}
                </select>
              </div>
              <div className="button-group">
                <button type="submit">Associate</button>
                <button type="button" className="button-secondary" onClick={() => setShowAssociateModal(false)}>
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
