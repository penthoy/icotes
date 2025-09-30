import { describe, it, expect, vi, beforeEach } from 'vitest';

// jsdom DragEvent polyfill
if (typeof (global as any).DragEvent === 'undefined') {
  class DragEventPolyfill extends Event {
    dataTransfer: any;
    constructor(type: string, eventInitDict: any = {}) {
      super(type, eventInitDict);
      this.dataTransfer = eventInitDict.dataTransfer || {
        files: [],
        types: ['Files'],
        items: []
      };
    }
  }
  ;(global as any).DragEvent = DragEventPolyfill as any;
}
import { render, act } from '@testing-library/react';
import React from 'react';
import GlobalUploadManager from '../../icui/components/media/GlobalUploadManager';

class MockXHR {
  upload = { addEventListener: vi.fn() } as any;
  addEventListener = vi.fn((event: string, cb: any) => {
    if (event === 'load') {
      (this as any)._load = cb;
    }
  });
  open = vi.fn();
  send = vi.fn(() => {
    setTimeout(() => {
      (this as any).status = 200;
      (this as any).responseText = JSON.stringify({ attachment: { id: 'abc', filename: 'f.txt', mime_type: 'text/plain', kind: 'files' } });
      (this as any)._load && (this as any)._load();
    }, 10);
  });
  abort = vi.fn();
}
// @ts-ignore
global.XMLHttpRequest = MockXHR;
(Object.assign(window, { __ICOTES_CONFIG__: { api_url: '/api' } }));
// @ts-ignore
global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));

describe('GlobalUploadManager', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  it('opens on custom event and multi-file paste', async () => {
    render(<GlobalUploadManager />);
    
    // Trigger explicit open request (from Explorer multi-file drop)
    await act(async () => {
      window.dispatchEvent(new CustomEvent('icotes:open-upload-widget'));
      await vi.runAllTimersAsync();
    });
    
    // Simulate multi-file paste -> should also auto-open and enqueue
    const f1 = new File(['a'], 'a.txt', { type: 'text/plain' });
    const f2 = new File(['b'], 'b.txt', { type: 'text/plain' });
    const pasteEvent: any = new Event('paste');
    Object.defineProperty(pasteEvent, 'clipboardData', { value: { items: [{ kind: 'file', getAsFile: () => f1 }, { kind: 'file', getAsFile: () => f2 }] } });
    
    await act(async () => {
      window.dispatchEvent(pasteEvent);
      await vi.runAllTimersAsync();
    });
  });
});
