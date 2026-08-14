import { Router } from 'express';
import { haClient } from '../services/homeassistant';

const router = Router();

// Get HA connection status
router.get('/status', async (req, res) => {
  try {
    const status = await haClient.getStatus();
    res.json(status);
  } catch (error) {
    res.status(500).json({ error: 'Failed to connect to Home Assistant' });
  }
});

// Get person entities from HA
router.get('/persons', async (req, res) => {
  try {
    const persons = await haClient.getPersons();
    res.json(persons);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch persons from Home Assistant' });
  }
});

// Update person location in HA
router.post('/persons/:personId/location', async (req, res) => {
  try {
    const { zone } = req.body;
    await haClient.updatePersonLocation(req.params.personId, zone);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update person location' });
  }
});

// Get device tracker entities from HA
router.get('/device-trackers', async (req, res) => {
  try {
    const trackers = await haClient.getDeviceTrackers();
    res.json(trackers);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch device trackers' });
  }
});

// Send event to HA
router.post('/events', async (req, res) => {
  try {
    const { eventType, data } = req.body;
    await haClient.sendEvent(eventType, data);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Failed to send event to Home Assistant' });
  }
});

export default router;
