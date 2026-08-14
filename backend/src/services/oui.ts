// OUI (Organizationally Unique Identifier) Database
// Maps MAC address prefixes to manufacturers

interface OUIEntry {
  prefix: string;
  vendor: string;
}

class OUIDatabase {
  private database: OUIEntry[] = [
    // Common manufacturers (sample data - in production, load from file or API)
    { prefix: '00:00:00', vendor: 'Xerox Corporation' },
    { prefix: '00:01:42', vendor: 'Cisco Systems' },
    { prefix: '00:03:93', vendor: 'Apple Inc.' },
    { prefix: '00:04:20', vendor: 'Cisco Systems' },
    { prefix: '00:0A:95', vendor: 'Apple Inc.' },
    { prefix: '00:0D:93', vendor: 'Apple Inc.' },
    { prefix: '00:11:24', vendor: 'Apple Inc.' },
    { prefix: '00:14:51', vendor: 'Apple Inc.' },
    { prefix: '00:16:CB', vendor: 'Apple Inc.' },
    { prefix: '00:17:F2', vendor: 'Apple Inc.' },
    { prefix: '00:19:E3', vendor: 'Apple Inc.' },
    { prefix: '00:1B:63', vendor: 'Apple Inc.' },
    { prefix: '00:1C:B3', vendor: 'Apple Inc.' },
    { prefix: '00:1E:52', vendor: 'Apple Inc.' },
    { prefix: '00:1F:5B', vendor: 'Apple Inc.' },
    { prefix: '00:21:E9', vendor: 'Apple Inc.' },
    { prefix: '00:22:41', vendor: 'Apple Inc.' },
    { prefix: '00:23:12', vendor: 'Apple Inc.' },
    { prefix: '00:23:32', vendor: 'Apple Inc.' },
    { prefix: '00:23:6C', vendor: 'Apple Inc.' },
    { prefix: '00:23:DF', vendor: 'Apple Inc.' },
    { prefix: '00:24:36', vendor: 'Apple Inc.' },
    { prefix: '00:25:00', vendor: 'Apple Inc.' },
    { prefix: '00:25:4B', vendor: 'Apple Inc.' },
    { prefix: '00:25:BC', vendor: 'Apple Inc.' },
    { prefix: '00:26:08', vendor: 'Apple Inc.' },
    { prefix: '00:26:4A', vendor: 'Apple Inc.' },
    { prefix: '00:26:B0', vendor: 'Apple Inc.' },
    { prefix: '00:26:BB', vendor: 'Apple Inc.' },
    { prefix: '00:50:56', vendor: 'VMware Inc.' },
    { prefix: '00:0C:29', vendor: 'VMware Inc.' },
    { prefix: '00:05:69', vendor: 'VMware Inc.' },
    { prefix: '08:00:27', vendor: 'Oracle VirtualBox' },
    { prefix: '52:54:00', vendor: 'QEMU Virtual NIC' },
    { prefix: '00:15:5D', vendor: 'Microsoft Hyper-V' },
    { prefix: '00:03:FF', vendor: 'Microsoft' },
    { prefix: '00:0D:3A', vendor: 'Microsoft Azure' },
    { prefix: 'DC:A6:32', vendor: 'Raspberry Pi Foundation' },
    { prefix: 'B8:27:EB', vendor: 'Raspberry Pi Foundation' },
    { prefix: 'E4:5F:01', vendor: 'Raspberry Pi Foundation' },
    { prefix: '28:CD:C1', vendor: 'Raspberry Pi Foundation' },
    { prefix: 'D8:3A:DD', vendor: 'Raspberry Pi Foundation' },
    { prefix: '00:1B:44', vendor: 'Samsung Electronics' },
    { prefix: '00:12:FB', vendor: 'Samsung Electronics' },
    { prefix: '00:13:77', vendor: 'Samsung Electronics' },
    { prefix: '00:15:B9', vendor: 'Samsung Electronics' },
    { prefix: '00:16:32', vendor: 'Samsung Electronics' },
    { prefix: '00:16:6B', vendor: 'Samsung Electronics' },
    { prefix: '00:16:6C', vendor: 'Samsung Electronics' },
    { prefix: '00:17:C9', vendor: 'Samsung Electronics' },
    { prefix: '00:18:AF', vendor: 'Samsung Electronics' },
    { prefix: '00:1A:8A', vendor: 'Samsung Electronics' },
    { prefix: '74:45:CE', vendor: 'Ubiquiti Networks' },
    { prefix: '68:D7:9A', vendor: 'Ubiquiti Networks' },
    { prefix: 'F0:9F:C2', vendor: 'Ubiquiti Networks' },
    { prefix: '04:18:D6', vendor: 'Ubiquiti Networks' },
    { prefix: '24:A4:3C', vendor: 'Ubiquiti Networks' },
    { prefix: 'DC:9F:DB', vendor: 'Ubiquiti Networks' },
    { prefix: 'E0:63:DA', vendor: 'Ubiquiti Networks' },
    { prefix: 'FC:EC:DA', vendor: 'Ubiquiti Networks' },
    { prefix: '00:27:22', vendor: 'Ubiquiti Networks' },
  ];

  lookup(mac: string): string | null {
    // Normalize MAC address
    const normalized = mac.toUpperCase().replace(/[:-]/g, '');
    
    // Extract OUI (first 6 characters / 3 bytes)
    if (normalized.length < 6) {
      return null;
    }
    
    const oui = normalized.substring(0, 6);
    const formatted = `${oui.substring(0, 2)}:${oui.substring(2, 4)}:${oui.substring(4, 6)}`;
    
    const entry = this.database.find(e => e.prefix === formatted);
    return entry ? entry.vendor : null;
  }

  search(query: string): OUIEntry[] {
    const lowerQuery = query.toLowerCase();
    return this.database.filter(entry => 
      entry.vendor.toLowerCase().includes(lowerQuery) ||
      entry.prefix.toLowerCase().includes(lowerQuery)
    );
  }

  getStats() {
    return {
      totalEntries: this.database.length,
      vendors: new Set(this.database.map(e => e.vendor)).size,
    };
  }
}

export const ouiDatabase = new OUIDatabase();
