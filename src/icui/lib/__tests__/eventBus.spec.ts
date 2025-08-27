import { describe, it, expect, vi, beforeEach } from 'vitest';
import { emitSessionChange, subscribeSessionChange, __resetEventBusForTests } from '../eventBus';

describe('eventBus dedupe', () => {
  beforeEach(() => {
    __resetEventBusForTests();
  });

  it('drops duplicate events within 150ms window', async () => {
    const cb = vi.fn();
    const unsub = subscribeSessionChange(cb);

    const ts = Date.now();
    emitSessionChange({ action: 'switch', sessionId: 'A', ts });
    emitSessionChange({ action: 'switch', sessionId: 'A', ts: ts + 50 });

    // Allow microtask queue to flush
    await new Promise(r => setTimeout(r, 10));

    expect(cb).toHaveBeenCalledTimes(1);
    unsub();
  });

  it('emits again after window elapses', async () => {
    const cb = vi.fn();
    const unsub = subscribeSessionChange(cb);

    // Use synthetic timestamps to bypass timing flake
    emitSessionChange({ action: 'switch', sessionId: 'A', ts: 1000 });
    emitSessionChange({ action: 'switch', sessionId: 'A', ts: 1200 }); // still within 150ms? No, boundary: 200ms > 150ms

    expect(cb).toHaveBeenCalledTimes(2);
    unsub();
  });
});
