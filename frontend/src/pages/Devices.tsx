import { useEffect, useState } from 'react';
import api from '../api';

interface Device {
  id: string;
  mac: string;
  name: string;
  personId?: string;
  lastSeen?: string;
}

interface Person {
  id: string;
  name: string;
}

function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [persons, setPersons] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [formData, setFormData] = useState({ mac: '', name: '', personId: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [devicesRes, personsRes] = await Promise.all([
        api.get('/devices'),
        api.get('/persons'),
      ]);
      setDevices(devicesRes.data);
      setPersons(personsRes.data);
    } catch (err) {
      console.error('Failed to load devices:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingDevice(null);
    setFormData({ mac: '', name: '', personId: '' });
    setShowModal(true);
  };

  const handleEdit = (device: Device) => {
    setEditingDevice(device);
    setFormData({ 
      mac: device.mac, 
      name: device.name, 
      personId: device.personId || '' 
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this device?')) return;
    
    try {
      await api.delete(`/devices/${id}`);
      fetchData();
    } catch (err) {
      console.error('Failed to delete device:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (editingDevice) {
        await api.put(`/devices/${editingDevice.id}`, formData);
      } else {
        await api.post('/devices', formData);
      }
      setShowModal(false);
      fetchData();
    } catch (err) {
      console.error('Failed to save device:', err);
    }
  };

  const getPersonName = (personId?: string) => {
    if (!personId) return '-';
    const person = persons.find(p => p.id === personId);
    return person?.name || '-';
  };

  if (loading) {
    return <div className="loading">Loading devices...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Device Management</h2>
            <p>Manage tracked devices and their associations</p>
          </div>
          <button onClick={handleAdd}>Add Device</button>
        </div>
      </div>

      {devices.length === 0 ? (
        <div className="empty-state">
          <h3>No devices yet</h3>
          <p>Add your first device to start tracking</p>
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>MAC Address</th>
                <th>Person</th>
                <th>Last Seen</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {devices.map(device => (
                <tr key={device.id}>
                  <td>{device.name}</td>
                  <td><code>{device.mac}</code></td>
                  <td>{getPersonName(device.personId)}</td>
                  <td>{device.lastSeen ? new Date(device.lastSeen).toLocaleString() : '-'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button onClick={() => handleEdit(device)}>Edit</button>
                      <button className="button-danger" onClick={() => handleDelete(device.id)}>Delete</button>
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
            <h3>{editingDevice ? 'Edit Device' : 'Add Device'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>MAC Address</label>
                <input
                  type="text"
                  value={formData.mac}
                  onChange={(e) => setFormData({ ...formData, mac: e.target.value })}
                  placeholder="00:11:22:33:44:55"
                  required
                />
              </div>
              <div className="form-group">
                <label>Assign to Person (optional)</label>
                <select
                  value={formData.personId}
                  onChange={(e) => setFormData({ ...formData, personId: e.target.value })}
                >
                  <option value="">None</option>
                  {persons.map(person => (
                    <option key={person.id} value={person.id}>{person.name}</option>
                  ))}
                </select>
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

export default Devices;
