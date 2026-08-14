import { Router } from 'express';
import { ouiDatabase } from '../services/oui';

const router = Router();

// Lookup OUI by MAC address
router.get('/lookup/:mac', (req, res) => {
  const vendor = ouiDatabase.lookup(req.params.mac);
  res.json({ mac: req.params.mac, vendor });
});

// Search OUI database
router.get('/search', (req, res) => {
  const { query } = req.query;
  if (!query || typeof query !== 'string') {
    return res.status(400).json({ error: 'Query parameter required' });
  }
  const results = ouiDatabase.search(query);
  res.json(results);
});

// Get database stats
router.get('/stats', (req, res) => {
  const stats = ouiDatabase.getStats();
  res.json(stats);
});

export default router;
