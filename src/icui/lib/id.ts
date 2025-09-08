/**
 * Safe ID/UUID utilities with robust fallbacks.
 *
 * Uses crypto.randomUUID when available; otherwise falls back to
 * RFC4122 v4 generation via crypto.getRandomValues, and finally
 * to Math.random with a timestamp to minimize collision risk.
 */

function uuidFromGetRandomValues(): string | null {
  try {
    const gcrypto = (globalThis as any).crypto as Crypto | undefined;
    if (!gcrypto || typeof gcrypto.getRandomValues !== 'function') return null;
    const bytes = new Uint8Array(16);
    gcrypto.getRandomValues(bytes);

    // Per RFC4122 v4
    bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10

    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return (
      hex.slice(0, 8) + '-' +
      hex.slice(8, 12) + '-' +
      hex.slice(12, 16) + '-' +
      hex.slice(16, 20) + '-' +
      hex.slice(20)
    );
  } catch {
    return null;
  }
}

function bestUUID(): string {
  try {
    const gcrypto = (globalThis as any).crypto as Crypto | undefined;
    if (gcrypto && typeof (gcrypto as any).randomUUID === 'function') {
      return (gcrypto as any).randomUUID();
    }
  } catch {
    // ignore
  }

  const v4 = uuidFromGetRandomValues();
  if (v4) return v4;

  // Last-resort fallback: Math.random + timestamp
  return (
    Date.now().toString(36) + '-' + Math.random().toString(36).slice(2) + '-' +
    Math.random().toString(36).slice(2)
  );
}

/**
 * Generate a reasonably unique ID with an optional prefix.
 */
export function randomId(prefix = 'id'): string {
  const core = bestUUID();
  return prefix ? `${prefix}_${core}` : core;
}
