import { Router } from 'express';
import { storage } from '../storage';
import { broadcast } from '../index';

const router = Router();

// Get all persons
router.get('/', (req, res) => {
  const persons = storage.getPersons();
  res.json(persons);
});

// Get person by ID
router.get('/:id', (req, res) => {
  const person = storage.getPerson(req.params.id);
  if (!person) {
    return res.status(404).json({ error: 'Person not found' });
  }
  res.json(person);
});

// Create person
router.post('/', (req, res) => {
  const person = storage.addPerson(req.body);
  broadcast({ type: 'person_added', person });
  res.status(201).json(person);
});

// Update person
router.put('/:id', (req, res) => {
  const person = storage.updatePerson(req.params.id, req.body);
  if (!person) {
    return res.status(404).json({ error: 'Person not found' });
  }
  broadcast({ type: 'person_updated', person });
  res.json(person);
});

// Delete person
router.delete('/:id', (req, res) => {
  const deleted = storage.deletePerson(req.params.id);
  if (!deleted) {
    return res.status(404).json({ error: 'Person not found' });
  }
  broadcast({ type: 'person_deleted', id: req.params.id });
  res.status(204).send();
});

// Assign device to person
router.post('/:id/devices', (req, res) => {
  const { deviceId } = req.body;
  const person = storage.assignDeviceToPerson(req.params.id, deviceId);
  if (!person) {
    return res.status(404).json({ error: 'Person not found' });
  }
  broadcast({ type: 'person_updated', person });
  res.json(person);
});

export default router;
