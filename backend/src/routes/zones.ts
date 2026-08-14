import { Router } from 'express';
import { storage } from '../storage';
import { broadcast } from '../index';

const router = Router();

// Get all zones
router.get('/', (req, res) => {
  const zones = storage.getZones();
  res.json(zones);
});

// Get zone by ID
router.get('/:id', (req, res) => {
  const zone = storage.getZone(req.params.id);
  if (!zone) {
    return res.status(404).json({ error: 'Zone not found' });
  }
  res.json(zone);
});

// Create zone
router.post('/', (req, res) => {
  const zone = storage.addZone(req.body);
  broadcast({ type: 'zone_added', zone });
  res.status(201).json(zone);
});

// Update zone
router.put('/:id', (req, res) => {
  const zone = storage.updateZone(req.params.id, req.body);
  if (!zone) {
    return res.status(404).json({ error: 'Zone not found' });
  }
  broadcast({ type: 'zone_updated', zone });
  res.json(zone);
});

// Delete zone
router.delete('/:id', (req, res) => {
  const deleted = storage.deleteZone(req.params.id);
  if (!deleted) {
    return res.status(404).json({ error: 'Zone not found' });
  }
  broadcast({ type: 'zone_deleted', id: req.params.id });
  res.status(204).send();
});

// Map AP to zone
router.post('/:id/aps', (req, res) => {
  const { apId } = req.body;
  const zone = storage.mapApToZone(req.params.id, apId);
  if (!zone) {
    return res.status(404).json({ error: 'Zone not found' });
  }
  broadcast({ type: 'zone_updated', zone });
  res.json(zone);
});

// Remove AP from zone
router.delete('/:id/aps/:apId', (req, res) => {
  const zone = storage.removeApFromZone(req.params.id, req.params.apId);
  if (!zone) {
    return res.status(404).json({ error: 'Zone not found' });
  }
  broadcast({ type: 'zone_updated', zone });
  res.json(zone);
});

export default router;
