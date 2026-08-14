import { Router } from 'express';
import { storage } from '../storage';
import { broadcast } from '../index';

const router = Router();

// Get all devices
router.get('/', (req, res) => {
  const devices = storage.getDevices();
  res.json(devices);
});

// Get device by ID
router.get('/:id', (req, res) => {
  const device = storage.getDevice(req.params.id);
  if (!device) {
    return res.status(404).json({ error: 'Device not found' });
  }
  res.json(device);
});

// Create device
router.post('/', (req, res) => {
  const device = storage.addDevice(req.body);
  broadcast({ type: 'device_added', device });
  res.status(201).json(device);
});

// Update device
router.put('/:id', (req, res) => {
  const device = storage.updateDevice(req.params.id, req.body);
  if (!device) {
    return res.status(404).json({ error: 'Device not found' });
  }
  broadcast({ type: 'device_updated', device });
  res.json(device);
});

// Delete device
router.delete('/:id', (req, res) => {
  const deleted = storage.deleteDevice(req.params.id);
  if (!deleted) {
    return res.status(404).json({ error: 'Device not found' });
  }
  broadcast({ type: 'device_deleted', id: req.params.id });
  res.status(204).send();
});

export default router;
