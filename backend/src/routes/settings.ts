import { Router } from 'express';
import { storage } from '../storage';

const router = Router();

// Get all settings
router.get('/', (req, res) => {
  const settings = storage.getSettings();
  res.json(settings);
});

// Update settings
router.put('/', (req, res) => {
  const settings = storage.updateSettings(req.body);
  res.json(settings);
});

// Get specific setting
router.get('/:key', (req, res) => {
  const value = storage.getSetting(req.params.key);
  if (value === undefined) {
    return res.status(404).json({ error: 'Setting not found' });
  }
  res.json({ key: req.params.key, value });
});

// Set specific setting
router.put('/:key', (req, res) => {
  const { value } = req.body;
  storage.setSetting(req.params.key, value);
  res.json({ key: req.params.key, value });
});

export default router;
