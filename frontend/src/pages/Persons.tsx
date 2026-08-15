import { useEffect, useState } from 'react';
import api from '../api';

interface Person {
  id: string;
  name: string;
  deviceIds: string[];
  haEntityId?: string;
}

function Persons() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [formData, setFormData] = useState({ name: '', haEntityId: '' });

  useEffect(() => {
    fetchPersons();
  }, []);

  const fetchPersons = async () => {
    try {
      const res = await api.get('/persons');
      setPersons(res.data);
    } catch (err) {
      console.error('Failed to load persons:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingPerson(null);
    setFormData({ name: '', haEntityId: '' });
    setShowModal(true);
  };

  const handleEdit = (person: Person) => {
    setEditingPerson(person);
    setFormData({ 
      name: person.name, 
      haEntityId: person.haEntityId || '' 
    });
    setShowModal(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this person?')) return;
    
    try {
      await api.delete(`/persons/${id}`);
      fetchPersons();
    } catch (err) {
      console.error('Failed to delete person:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      if (editingPerson) {
        await api.put(`/persons/${editingPerson.id}`, formData);
      } else {
        await api.post('/persons', { ...formData, deviceIds: [] });
      }
      setShowModal(false);
      fetchPersons();
    } catch (err) {
      console.error('Failed to save person:', err);
    }
  };

  if (loading) {
    return <div className="loading">Loading persons...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>Person Management</h2>
            <p>Manage people and their device associations</p>
          </div>
          <button onClick={handleAdd}>Add Person</button>
        </div>
      </div>

      {persons.length === 0 ? (
        <div className="empty-state">
          <h3>No persons yet</h3>
          <p>Add your first person to start tracking</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {persons.map(person => (
            <div key={person.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <h3>{person.name}</h3>
                  {person.haEntityId && (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      HA: {person.haEntityId}
                    </p>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => handleEdit(person)}>Edit</button>
                  <button className="button-danger" onClick={() => handleDelete(person.id)}>Delete</button>
                </div>
              </div>
              <div style={{ marginTop: '1rem' }}>
                <strong>Devices:</strong> {person.deviceIds.length || 0}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editingPerson ? 'Edit Person' : 'Add Person'}</h3>
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
                <label>Home Assistant Entity ID (optional)</label>
                <input
                  type="text"
                  value={formData.haEntityId}
                  onChange={(e) => setFormData({ ...formData, haEntityId: e.target.value })}
                  placeholder="person.john_doe"
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
