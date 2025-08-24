// Typed event bus with simple dedupe and self-ignore support

export type SessionChangeAction = 'switch' | 'create' | 'delete';

export interface SessionChangeEventPayload {
  sessionId: string;
  action: SessionChangeAction;
  sessionName?: string;
  prevSessionId?: string;
  source?: string; // component/module id to self-ignore
  ts?: number; // epoch ms
}

type SessionChangeListener = (payload: SessionChangeEventPayload) => void;

const listeners = new Set<SessionChangeListener>();

let lastEventKey = '';
let lastEventTs = 0;
const DEDUPE_WINDOW_MS = 150;

export function emitSessionChange(payload: SessionChangeEventPayload) {
  const ts = payload.ts ?? Date.now();
  const key = `${payload.action}:${payload.sessionId}`;
  if (key === lastEventKey && ts - lastEventTs <= DEDUPE_WINDOW_MS) {
    return; // drop duplicate burst
  }
  lastEventKey = key;
  lastEventTs = ts;

  for (const cb of Array.from(listeners)) {
    try {
      cb({ ...payload, ts });
    } catch {
      // ignore listener errors
    }
  }
}

export function subscribeSessionChange(callback: SessionChangeListener): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

// Test-only: reset internal dedupe state
export function __resetEventBusForTests() {
  lastEventKey = '';
  lastEventTs = 0;
}
