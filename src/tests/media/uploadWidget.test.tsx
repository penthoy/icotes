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
import { render } from '@testing-library/react';
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
  it('opens on dragover with files and handles drop', async () => {
    render(<GlobalUploadManager />);
    const dragEvent = new DragEvent('dragover', { bubbles: true });
    Object.defineProperty(dragEvent, 'dataTransfer', { value: { types: ['Files'] } });
    window.dispatchEvent(dragEvent);
    const file = new File(['hello'], 'f.txt', { type: 'text/plain' });
    const dropEvent: any = new DragEvent('drop', { bubbles: true });
    Object.defineProperty(dropEvent, 'dataTransfer', { value: { types: ['Files'], files: [file] } });
    window.dispatchEvent(dropEvent);
    await vi.runAllTimersAsync();
  });
});
