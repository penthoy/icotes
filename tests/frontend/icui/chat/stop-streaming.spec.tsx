import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatBackendClient } from '../../../../src/icui/services/chat-backend-client-impl';

// Minimal test to verify client-side interrupt flips state and calls callbacks

describe('ChatBackendClient stop streaming', () => {
  let client: ChatBackendClient;
  const events: any[] = [];

  beforeEach(() => {
    client = new ChatBackendClient();
    // mock internal enhanced service to avoid real websockets
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (client as any)['enhancedService'] = {
      sendMessage: vi.fn(async () => {}),
      on: vi.fn()
    } as any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(client as any)['connectionId'] = 'test-conn';
    client.onTyping((t) => events.push(['typing', t]));
  });

  it('interrupts locally and stops typing', async () => {
    // simulate stream start
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(client as any)['handleStreamingMessage']({ stream_start: true, id: 'm1' });
    expect(client.streamingStatus).toBe(true);

    await client.stopStreaming();

    expect(client.streamingStatus).toBe(false);
    // last typing event should be false
    const lastTyping = events.filter(e => e[0] === 'typing').pop();
    expect(lastTyping?.[1]).toBe(false);

    // simulate a stray chunk after stop should be ignored
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(client as any)['handleStreamingMessage']({ stream_chunk: true, chunk: 'ignored' });
    expect(client.streamingStatus).toBe(false);
  });
});
