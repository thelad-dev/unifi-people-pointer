import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Devices from './pages/Devices';
import Persons from './pages/Persons';
import Zones from './pages/Zones';
import UnknownClients from './pages/UnknownClients';
import OUIDatabase from './pages/OUIDatabase';
import Settings from './pages/Settings';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <h1>UniFi People Pointer</h1>
          </div>
          <ul className="navbar-menu">
            <li><Link to="/">Dashboard</Link></li>
            <li><Link to="/devices">Devices</Link></li>
            <li><Link to="/persons">Persons</Link></li>
            <li><Link to="/zones">Zones</Link></li>
            <li><Link to="/unknown-clients">Unknown Clients</Link></li>
            <li><Link to="/oui">OUI Database</Link></li>
            <li><Link to="/settings">Settings</Link></li>
          </ul>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/devices" element={<Devices />} />
            <Route path="/persons" element={<Persons />} />
            <Route path="/zones" element={<Zones />} />
            <Route path="/unknown-clients" element={<UnknownClients />} />
            <Route path="/oui" element={<OUIDatabase />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
