import { useEffect, useState } from 'react';
import api from '../api';

interface Zone {
  id: string;
  name: string;
  apIds: string[];
  haZoneId?: string;
}

function Zones() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showApModal, setShowApModal] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [formData, setFormData] = useState({ name: '', haZoneId: '' });
  const [apId, setApId] = useState('');

  useEffect(() => {
    fetchZones();
  }, []);

  const fetchZones = async () => {
    try {
      const res = await api.get('/zones');
      setZones(res.data);
    } catch (err) {
      console.error('Failed to load zones:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingZone(null);
    setFormData({ name: '', haZoneId: '' });
    setShowModal(true);
  };

  const handleEdit = (zone: Zone) => {
    setEditingZone(zone);
    setFormData({ 
      name: zone.name, 
      haZoneId: zone.haZoneId || '' 
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this zone?')) return;
    
    try {
      await api.delete(`/zones/${id}`);
      fetchZones();
    } catch (err) {
      console.error('Failed to delete zone:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (editingZone) {
        await api.put(`/zones/${editingZone.id}`, formData);
      } else {
        await api.post('/zones', { ...formData, apIds: [] });
      }
      setShowModal(false);
      fetchZones();
    } catch (err) {
      console.error('Failed to save zone:', err);
    }
  };

  const handleManageAps = (zone: Zone) => {
    setSelectedZone(zone);
    setShowApModal(true);
  };

  const handleAddAp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedZone) return;

    try {
      await api.post(`/zones/${selectedZone.id}/aps`, { apId });
      setApId('');
      fetchZones();
    } catch (err) {
      console.error('Failed to add AP:', err);
    }
  };

  const handleRemoveAp = async (zoneId: string, apId: string) => {
    try {
      await api.delete(`/zones/${zoneId}/aps/${apId}`);
      fetchZones();
    } catch (err) {
      console.error('Failed to remove AP:', err);
    }
  };

  if (loading) {
    return <div className="loading">Loading zones...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Zone Management</h2>
            <p>Map Access Points to zones for location tracking</p>
          </div>
          <button onClick={handleAdd}>Add Zone</button>
        </div>
      </div>

      {zones.length === 0 ? (
        <div className="empty-state">
          <h3>No zones yet</h3>
          <p>Add your first zone to start mapping APs</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {zones.map(zone => (
            <div key={zone.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <h3>{zone.name}</h3>
                  {zone.haZoneId && (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      HA Zone: {zone.haZoneId}
                    </p>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => handleEdit(zone)}>Edit</button>
                  <button className="button-danger" onClick={() => handleDelete(zone.id)}>Delete</button>
                </div>
              </div>
              <div style={{ marginTop: '1rem' }}>
                <strong>Access Points:</strong> {zone.apIds.length || 0}
                {zone.apIds.length > 0 && (
                  <div style={{ marginTop: '0.5rem' }}>
                    {zone.apIds.map(apId => (
                      <span key={apId} className="badge badge-info" style={{ marginRight: '0.5rem' }}>
                        {apId}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button 
                onClick={() => handleManageAps(zone)} 
                style={{ marginTop: '1rem', width: '100%' }}
              >
                Manage APs
              </button>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editingZone ? 'Edit Zone' : 'Add Zone'}</h3>
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
                <label>Home Assistant Zone ID (optional)</label>
                <input
                  type="text"
                  value={formData.haZoneId}
                  onChange={(e) => setFormData({ ...formData, haZoneId: e.target.value })}
                  placeholder="zone.living_room"
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

      {showApModal && selectedZone && (
        <div className="modal-overlay" onClick={() => setShowApModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Manage APs for {selectedZone.name}</h3>
            
            <form onSubmit={handleAddAp} style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label>Add Access Point</label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={apId}
                    onChange={(e) => setApId(e.target.value)}
                    placeholder="AP MAC or ID"
                    style={{ flex: 1 }}
                  />
                  <button type="submit">Add</button>
                </div>
              </div>
            </form>

            {selectedZone.apIds.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)' }}>No APs assigned to this zone yet</p>
            ) : (
              <div>
                <h4>Assigned APs:</h4>
                <ul style={{ listStyle: 'none' }}>
                  {selectedZone.apIds.map(apId => (
                    <li key={apId} style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      padding: '0.5rem',
                      borderBottom: '1px solid var(--border)'
                    }}>
                      <code>{apId}</code>
                      <button 
                        className="button-danger" 
                        onClick={() => handleRemoveAp(selectedZone.id, apId)}
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="button-group">
              <button type="button" onClick={() => setShowApModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Zones;
