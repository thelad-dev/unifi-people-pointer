import fs from 'fs';
import path from 'path';

interface Device {
  id: string;
  mac: string;
  name: string;
  personId?: string;
  lastSeen?: string;
}

interface Person {
  id: string;
  name: string;
  deviceIds: string[];
  haEntityId?: string;
}

interface Zone {
  id: string;
  name: string;
  apIds: string[];
  haZoneId?: string;
}

interface Client {
  mac: string;
  hostname?: string;
  vendor?: string;
  lastSeen: string;
  ignored?: boolean;
  personId?: string;
}

interface Settings {
  haUrl?: string;
  haToken?: string;
  unifiController?: string;
  unifiUsername?: string;
  unifiPassword?: string;
  [key: string]: any;
}

class Storage {
  private dataDir = process.env.DATA_DIR || '/data';
  private devices: Map<string, Device> = new Map();
  private persons: Map<string, Person> = new Map();
  private zones: Map<string, Zone> = new Map();
  private clients: Map<string, Client> = new Map();
  private settings: Settings = {};

  constructor() {
    this.ensureDataDir();
    this.load();
  }

  private ensureDataDir() {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  private load() {
    this.loadJson('devices.json', this.devices);
    this.loadJson('persons.json', this.persons);
    this.loadJson('zones.json', this.zones);
    this.loadJson('clients.json', this.clients);
    this.settings = this.loadSettings();
  }

  private loadJson(filename: string, target: Map<string, any>) {
    const filepath = path.join(this.dataDir, filename);
    if (fs.existsSync(filepath)) {
      try {
        const data = JSON.parse(fs.readFileSync(filepath, 'utf-8'));
        Object.entries(data).forEach(([key, value]) => {
          target.set(key, value);
        });
      } catch (error) {
        console.error(`Failed to load ${filename}:`, error);
      }
    }
  }

  private loadSettings(): Settings {
    const filepath = path.join(this.dataDir, 'settings.json');
    if (fs.existsSync(filepath)) {
      try {
        return JSON.parse(fs.readFileSync(filepath, 'utf-8'));
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    }
    return {};
  }

  private save(filename: string, data: Map<string, any>) {
    const filepath = path.join(this.dataDir, filename);
    const obj = Object.fromEntries(data);
    fs.writeFileSync(filepath, JSON.stringify(obj, null, 2));
  }

  private saveSettings() {
    const filepath = path.join(this.dataDir, 'settings.json');
    fs.writeFileSync(filepath, JSON.stringify(this.settings, null, 2));
  }

  // Devices
  getDevices() {
    return Array.from(this.devices.values());
  }

  getDevice(id: string) {
    return this.devices.get(id);
  }

  addDevice(device: Omit<Device, 'id'>) {
    const id = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newDevice = { ...device, id };
    this.devices.set(id, newDevice);
    this.save('devices.json', this.devices);
    return newDevice;
  }

  updateDevice(id: string, updates: Partial<Device>) {
    const device = this.devices.get(id);
    if (!device) return null;
    const updated = { ...device, ...updates };
    this.devices.set(id, updated);
    this.save('devices.json', this.devices);
    return updated;
  }

  deleteDevice(id: string) {
    const result = this.devices.delete(id);
    if (result) {
      this.save('devices.json', this.devices);
    }
    return result;
  }

  // Persons
  getPersons() {
    return Array.from(this.persons.values());
  }

  getPerson(id: string) {
    return this.persons.get(id);
  }

  addPerson(person: Omit<Person, 'id'>) {
    const id = `person_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newPerson = { ...person, id, deviceIds: person.deviceIds || [] };
    this.persons.set(id, newPerson);
    this.save('persons.json', this.persons);
    return newPerson;
  }

  updatePerson(id: string, updates: Partial<Person>) {
    const person = this.persons.get(id);
    if (!person) return null;
    const updated = { ...person, ...updates };
    this.persons.set(id, updated);
    this.save('persons.json', this.persons);
    return updated;
  }

  deletePerson(id: string) {
    const result = this.persons.delete(id);
    if (result) {
      this.save('persons.json', this.persons);
    }
    return result;
  }

  assignDeviceToPerson(personId: string, deviceId: string) {
    const person = this.persons.get(personId);
    if (!person) return null;
    if (!person.deviceIds.includes(deviceId)) {
      person.deviceIds.push(deviceId);
    }
    this.updateDevice(deviceId, { personId });
    this.save('persons.json', this.persons);
    return person;
  }

  // Zones
  getZones() {
    return Array.from(this.zones.values());
  }

  getZone(id: string) {
    return this.zones.get(id);
  }

  addZone(zone: Omit<Zone, 'id'>) {
    const id = `zone_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newZone = { ...zone, id, apIds: zone.apIds || [] };
    this.zones.set(id, newZone);
    this.save('zones.json', this.zones);
    return newZone;
  }

  updateZone(id: string, updates: Partial<Zone>) {
    const zone = this.zones.get(id);
    if (!zone) return null;
    const updated = { ...zone, ...updates };
    this.zones.set(id, updated);
    this.save('zones.json', this.zones);
    return updated;
  }

  deleteZone(id: string) {
    const result = this.zones.delete(id);
    if (result) {
      this.save('zones.json', this.zones);
    }
    return result;
  }

  mapApToZone(zoneId: string, apId: string) {
    const zone = this.zones.get(zoneId);
    if (!zone) return null;
    if (!zone.apIds.includes(apId)) {
      zone.apIds.push(apId);
      this.save('zones.json', this.zones);
    }
    return zone;
  }

  removeApFromZone(zoneId: string, apId: string) {
    const zone = this.zones.get(zoneId);
    if (!zone) return null;
    zone.apIds = zone.apIds.filter(id => id !== apId);
    this.save('zones.json', this.zones);
    return zone;
  }

  // Clients
  getClients() {
    return Array.from(this.clients.values());
  }

  getUnknownClients() {
    return Array.from(this.clients.values()).filter(
      client => !client.ignored && !client.personId
    );
  }

  ignoreClient(mac: string) {
    const client = this.clients.get(mac) || {
      mac,
      lastSeen: new Date().toISOString()
    };
    client.ignored = true;
    this.clients.set(mac, client);
    this.save('clients.json', this.clients);
    return client;
  }

  associateClient(mac: string, personId: string) {
    const client = this.clients.get(mac) || {
      mac,
      lastSeen: new Date().toISOString()
    };
    client.personId = personId;
    this.clients.set(mac, client);
    this.save('clients.json', this.clients);
    return client;
  }

  updateClient(mac: string, updates: Partial<Client>) {
    const client = this.clients.get(mac) || { mac, lastSeen: new Date().toISOString() };
    const updated = { ...client, ...updates };
    this.clients.set(mac, updated);
    this.save('clients.json', this.clients);
    return updated;
  }

  // Settings
  getSettings() {
    return this.settings;
  }

  getSetting(key: string) {
    return this.settings[key];
  }

  setSetting(key: string, value: any) {
    this.settings[key] = value;
    this.saveSettings();
  }

  updateSettings(updates: Partial<Settings>) {
    this.settings = { ...this.settings, ...updates };
    this.saveSettings();
    return this.settings;
  }
}

export const storage = new Storage();
