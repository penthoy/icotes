import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import React from 'react';
import { useMediaUpload } from '../../../../../src/icui/hooks/useMediaUpload';
import ChatDropZone from '../../../../../src/icui/components/media/ChatDropZone';

// Minimal mock for useMediaUpload so type not required from hook export
vi.mock('../../../../../src/icui/hooks/useMediaUpload', () => ({
  useMediaUpload: () => ({ addFiles: () => {} })
}));

describe('ChatDropZone highlight', () => {
  beforeAll(() => {
    if (typeof (global as any).DragEvent === 'undefined') {
      class PolyfillDragEvent extends Event {
        dataTransfer: any;
        constructor(type: string, init: any = {}) {
          super(type, init);
          this.dataTransfer = init.dataTransfer || { types: [], files: [] };
        }
      }
      ;(global as any).DragEvent = PolyfillDragEvent as any;
    }
  });
  it('shows and hides highlight on drag events', async () => {
  document.body.innerHTML = '<div class="icui-chat" style="position:relative;height:200px"><div class="icui-composer" data-chat-input style="position:relative"></div></div>';
    const uploadApi = useMediaUpload();
  const { container } = render(<ChatDropZone uploadApi={uploadApi as any} />);

  // Listeners are attached to the element with data-chat-input, not the outer chat container
  const target = document.querySelector('[data-chat-input]')!;

    const dt: any = { types: ['Files'], files: [] };
  const dragEnterEvent = new (global as any).DragEvent('dragenter', { bubbles: true, dataTransfer: dt });
  
  await act(async () => {
    target.dispatchEvent(dragEnterEvent);
  });

    await waitFor(() => {
      expect(document.body.textContent).toContain('Drop files to attach');
    });

    const dropEvent = new (global as any).DragEvent('drop', { bubbles: true, dataTransfer: dt });
    
    await act(async () => {
      target.dispatchEvent(dropEvent);
    });

    await waitFor(() => {
      // overlay should be removed
      expect(document.body.textContent).not.toContain('Drop files to attach');
    });
  });
});
