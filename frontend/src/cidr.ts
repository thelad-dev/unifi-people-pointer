// Client-side check of subnet input; the server validates again and stores
// the canonical form (network address plus prefix).

const IPV4_OCTET = /^(0|[1-9]\d{0,2})$/;

function isIpv4(address: string): boolean {
  const parts = address.split('.');
  return parts.length === 4 && parts.every((p) => IPV4_OCTET.test(p) && Number(p) <= 255);
}

function isIpv6(address: string): boolean {
  if (!address.includes(':') || !/^[0-9a-fA-F:.]+$/.test(address)) return false;
  try {
    // The URL parser implements the full IPv6 literal grammar.
    new URL(`http://[${address}]/`);
    return true;
  } catch {
    return false;
  }
}

// Return an error text for a subnet in CIDR notation, or null when it is valid.
// A bare address counts as a single host (/32 or /128).
export function cidrError(value: string): string | null {
  const text = value.trim();
  if (!text) return 'Enter a subnet such as 192.0.2.0/24.';
  const [address, prefix, ...rest] = text.split('/');
  if (rest.length) return `${text} is not a valid subnet.`;
  const v4 = isIpv4(address);
  if (!v4 && !isIpv6(address)) return `${address} is not an IPv4 or IPv6 address.`;
  if (prefix === undefined) return null;
  const max = v4 ? 32 : 128;
  if (!/^\d{1,3}$/.test(prefix) || Number(prefix) > max) {
    return `The prefix length must be between 0 and ${max}.`;
  }
  return null;
}

// Canonical form for IPv4 (network address plus prefix, as the server stores
// it); IPv6 input is passed on and canonicalized by the server.
export function canonicalCidr(value: string): string {
  const text = value.trim();
  const [address, prefix] = text.split('/');
  if (!isIpv4(address)) return text;
  const bits = prefix === undefined ? 32 : Number(prefix);
  const ip = address.split('.').reduce((acc, octet) => acc * 256 + Number(octet), 0);
  const size = 2 ** (32 - bits);
  const network = Math.floor(ip / size) * size;
  const octets = [24, 16, 8, 0].map((shift) => Math.floor(network / 2 ** shift) % 256);
  return `${octets.join('.')}/${bits}`;
}
