import { Router } from 'express';
import { storage } from '../storage';
import { broadcast } from '../index';

const router = Router();

// Get all unknown clients
router.get('/unknown', (req, res) => {
  const unknownClients = storage.getUnknownClients();
  res.json(unknownClients);
});

// Get all clients
router.get('/', (req, res) => {
  const clients = storage.getClients();
  res.json(clients);
});

// Mark client as known/ignore
router.post('/:mac/ignore', (req, res) => {
  const client = storage.ignoreClient(req.params.mac);
  broadcast({ type: 'client_ignored', mac: req.params.mac });
  res.json(client);
});

// Associate client with person
router.post('/:mac/associate', (req, res) => {
  const { personId } = req.body;
  const result = storage.associateClient(req.params.mac, personId);
  broadcast({ type: 'client_associated', mac: req.params.mac, personId });
  res.json(result);
});

export default router;
