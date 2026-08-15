import axios, { AxiosInstance } from 'axios';
import { storage } from '../storage';

class HomeAssistantClient {
  private client: AxiosInstance | null = null;

  private getClient(): AxiosInstance {
    const haUrl = storage.getSetting('haUrl');
    const haToken = storage.getSetting('haToken');

    if (!haUrl || !haToken) {
      throw new Error('Home Assistant URL and token must be configured');
    }

    if (!this.client) {
      this.client = axios.create({
        baseURL: haUrl,
        headers: {
          'Authorization': `Bearer ${haToken}`,
          'Content-Type': 'application/json',
        },
      });
    }

    return this.client;
  }

  async getStatus() {
    const client = this.getClient();
    const response = await client.get('/api/');
    return {
      connected: true,
      version: response.data.version,
      message: response.data.message,
    };
  }

  async getPersons() {
    const client = this.getClient();
    const response = await client.get('/api/states');
    const persons = response.data.filter((entity: any) => 
      entity.entity_id.startsWith('person.')
    );
    return persons;
  }

  async updatePersonLocation(personId: string, zone: string) {
    const client = this.getClient();
    await client.post('/api/services/device_tracker/see', {
      dev_id: personId,
      location_name: zone,
    });
  }

  async getDeviceTrackers() {
    const client = this.getClient();
    const response = await client.get('/api/states');
    const trackers = response.data.filter((entity: any) => 
      entity.entity_id.startsWith('device_tracker.')
    );
    return trackers;
  }

  async sendEvent(eventType: string, data: any) {
    const client = this.getClient();
    await client.post(`/api/events/${eventType}`, data);
  }

  async callService(domain: string, service: string, data: any) {
    const client = this.getClient();
    await client.post(`/api/services/${domain}/${service}`, data);
  }
}

export const haClient = new HomeAssistantClient();
