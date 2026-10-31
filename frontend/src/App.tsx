import { useEffect, useState } from 'react';
import Dashboard from './pages/Dashboard';
import Devices from './pages/Devices';
import Persons from './pages/Persons';
import UnknownClients from './pages/UnknownClients';
import AccessPoints from './pages/AccessPoints';
import { currentToken, embedded, onTokenChange, requestPanelToken, saveToken } from './api';
import './App.css';

function TokenGate() {
  const [value, setValue] = useState('');
  if (embedded) {
    return <div className="loading">Waiting for Home Assistant sign-in...</div>;
  }
  return (
    <div className="card token-card">
      <h3>Home Assistant access token</h3>
      <p>
        Open this page from the <strong>People Pointer</strong> entry in the Home Assistant
        sidebar, or paste a long-lived access token (Profile, Security) to use it directly.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) saveToken(value.trim());
        }}
      >
        <div className="form-group">
          <input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Long-lived access token"
            autoComplete="off"
          />
        </div>
        <button type="submit">Save token</button>
      </form>
    </div>
  );
}

const PAGES = [
  { hash: '', label: 'Overview', element: <Dashboard /> },
  { hash: 'persons', label: 'Persons', element: <Persons /> },
  { hash: 'devices', label: 'Devices', element: <Devices /> },
  { hash: 'unknown-clients', label: 'Unknown Clients', element: <UnknownClients /> },
  { hash: 'access-points', label: 'Access Points', element: <AccessPoints /> },
];

function currentHash(): string {
  return window.location.hash.replace(/^#\/?/, '');
}

function App() {
  const [token, setToken] = useState(currentToken());
  const [hash, setHash] = useState(currentHash());

  useEffect(() => {
    const off = onTokenChange(() => setToken(currentToken()));
    const onHash = () => setHash(currentHash());
    window.addEventListener('hashchange', onHash);
    // A token posted before this effect ran is stored but not announced.
    setToken(currentToken());
    requestPanelToken();
    return () => {
      off();
      window.removeEventListener('hashchange', onHash);
    };
  }, []);

  const page = PAGES.find((p) => p.hash === hash) || PAGES[0];

  return (
    <div className="app">
      <nav className="navbar">
        <div className="navbar-brand">
          <h1>UniFi People Pointer</h1>
        </div>
        <ul className="navbar-menu">
          {PAGES.map((p) => (
            <li key={p.hash}>
              <a href={`#/${p.hash}`} className={p === page ? 'active' : undefined}>
                {p.label}
              </a>
            </li>
          ))}
          {!embedded && token && (
            <li>
              <button className="button-secondary button-small" onClick={() => saveToken(null)}>
                Sign out
              </button>
            </li>
          )}
        </ul>
      </nav>
      <main className="main-content">{!token ? <TokenGate /> : page.element}</main>
    </div>
  );
}

export default App;
