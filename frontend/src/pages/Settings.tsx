import { useEffect, useState } from 'react';
import api from '../api';

interface Settings {
  haUrl?: string;
  haToken?: string;
  unifiController?: string;
  unifiUsername?: string;
  unifiPassword?: string;
}

function Settings() {
  const [settings, setSettings] = useState<Settings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [haStatus, setHaStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings');
      setSettings(res.data);
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      await api.put('/settings', settings);
      alert('Settings saved successfully');
    } catch (err) {
      console.error('Failed to save settings:', err);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const testHaConnection = async () => {
    try {
      const res = await api.get('/ha/status');
      setHaStatus(`Connected to Home Assistant ${res.data.version}`);
    } catch (err) {
      setHaStatus('Failed to connect to Home Assistant');
    }
  };

  if (loading) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure integrations and system settings</p>
      </div>

      <form onSubmit={handleSave}>
        <div className="card">
          <h3>Home Assistant Integration</h3>
          
          <div className="form-group">
            <label>Home Assistant URL</label>
            <input
              type="url"
              value={settings.haUrl || ''}
              onChange={(e) => setSettings({ ...settings, haUrl: e.target.value })}
              placeholder="http://homeassistant.local:8123"
            />
          </div>

          <div className="form-group">
            <label>Long-Lived Access Token</label>
            <input
              type="password"
              value={settings.haToken || ''}
              onChange={(e) => setSettings({ ...settings, haToken: e.target.value })}
              placeholder="Your Home Assistant token"
            />
          </div>

          <button type="button" className="button-secondary" onClick={testHaConnection}>
            Test Connection
          </button>

          {haStatus && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '0.75rem', 
              backgroundColor: haStatus.includes('Failed') ? 'var(--error)' : 'var(--success)',
              borderRadius: '4px',
              color: 'white'
            }}>
              {haStatus}
            </div>
          )}
        </div>

        <div className="card">
          <h3>UniFi Controller</h3>
          
          <div className="form-group">
            <label>Controller URL</label>
            <input
              type="url"
              value={settings.unifiController || ''}
              onChange={(e) => setSettings({ ...settings, unifiController: e.target.value })}
              placeholder="https://unifi.local:8443"
            />
          </div>

          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={settings.unifiUsername || ''}
              onChange={(e) => setSettings({ ...settings, unifiUsername: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={settings.unifiPassword || ''}
              onChange={(e) => setSettings({ ...settings, unifiPassword: e.target.value })}
            />
          </div>
        </div>

        <button type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}

export default Settings;
