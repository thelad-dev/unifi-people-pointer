import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { WebSocketServer } from 'ws';
import { createServer } from 'http';
import devicesRouter from './routes/devices';
import personsRouter from './routes/persons';
import zonesRouter from './routes/zones';
import clientsRouter from './routes/clients';
import ouiRouter from './routes/oui';
import haRouter from './routes/homeassistant';
import settingsRouter from './routes/settings';

dotenv.config();

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server });

const PORT = process.env.PORT || 3002;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/devices', devicesRouter);
app.use('/api/persons', personsRouter);
app.use('/api/zones', zonesRouter);
app.use('/api/clients', clientsRouter);
app.use('/api/oui', ouiRouter);
app.use('/api/ha', haRouter);
app.use('/api/settings', settingsRouter);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// WebSocket for live updates
wss.on('connection', (ws) => {
  console.log('WebSocket client connected');
  
  ws.on('message', (message) => {
    console.log('Received:', message.toString());
  });

  ws.on('close', () => {
    console.log('WebSocket client disconnected');
  });

  // Send initial connection message
  ws.send(JSON.stringify({ type: 'connected', timestamp: new Date().toISOString() }));
});

// Broadcast function for live updates
export function broadcast(data: any) {
  wss.clients.forEach((client) => {
    if (client.readyState === 1) { // WebSocket.OPEN
      client.send(JSON.stringify(data));
    }
  });
}

server.listen(PORT, () => {
  console.log(`UniFi People Pointer API running on port ${PORT}`);
});
