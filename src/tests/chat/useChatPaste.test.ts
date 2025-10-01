import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useChatPaste } from '../../icui/components/chat/hooks/useChatPaste';

// Mock the paste event
beforeEach(() => {
  vi.clearAllMocks();
});

describe('useChatPaste hook', () => {
  it('handles image paste events', () => {
    const stagePreview = vi.fn();
    const enqueueUploads = vi.fn();
    
    renderHook(() => useChatPaste(stagePreview, enqueueUploads));
    
    // Create a mock paste event with image files
    const imageFile = new File(['image data'], 'test.png', { type: 'image/png' });
    const mockClipboardItem = {
      kind: 'file',
      getAsFile: () => imageFile
    };
    
    const pasteEvent = new Event('paste') as any;
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: {
        items: [mockClipboardItem]
      }
    });
    
    // Dispatch the paste event
    window.dispatchEvent(pasteEvent);
    
    expect(stagePreview).toHaveBeenCalledWith(imageFile, 0, [imageFile]);
    expect(enqueueUploads).toHaveBeenCalledWith([imageFile]);
  });

  it('ignores non-image files', () => {
    const stagePreview = vi.fn();
    const enqueueUploads = vi.fn();
    
    renderHook(() => useChatPaste(stagePreview, enqueueUploads));
    
    // Create a mock paste event with text file
    const textFile = new File(['text data'], 'test.txt', { type: 'text/plain' });
    const mockClipboardItem = {
      kind: 'file',
      getAsFile: () => textFile
    };
    
    const pasteEvent = new Event('paste') as any;
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: {
        items: [mockClipboardItem]
      }
    });
    
    window.dispatchEvent(pasteEvent);
    
    expect(stagePreview).not.toHaveBeenCalled();
    expect(enqueueUploads).not.toHaveBeenCalled();
  });

  it('ignores events already handled by global handler', () => {
    const stagePreview = vi.fn();
    const enqueueUploads = vi.fn();
    
    renderHook(() => useChatPaste(stagePreview, enqueueUploads));
    
    const pasteEvent = new Event('paste') as any;
    pasteEvent._icuiGlobalPasteHandled = true;
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { items: [] }
    });
    
    window.dispatchEvent(pasteEvent);
    
    expect(stagePreview).not.toHaveBeenCalled();
    expect(enqueueUploads).not.toHaveBeenCalled();
  });

  it('handles events with no clipboard data', () => {
    const stagePreview = vi.fn();
    const enqueueUploads = vi.fn();
    
    renderHook(() => useChatPaste(stagePreview, enqueueUploads));
    
    const pasteEvent = new Event('paste');
    window.dispatchEvent(pasteEvent);
    
    expect(stagePreview).not.toHaveBeenCalled();
    expect(enqueueUploads).not.toHaveBeenCalled();
  });
});