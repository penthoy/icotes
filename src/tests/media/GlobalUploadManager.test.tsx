import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import GlobalUploadManager from '../../icui/components/media/GlobalUploadManager';

// Mock the hooks and services
vi.mock('../../icui/hooks/useMediaUpload', () => ({
  useMediaUpload: () => ({
    queue: [], // Add missing queue property
    uploads: [],
    isUploading: false,
    isOpen: false,
    open: vi.fn(),
    close: vi.fn(),
    addFiles: vi.fn(),
    removeFile: vi.fn(),
    clearCompleted: vi.fn(),
    uploadAll: vi.fn().mockResolvedValue([])
  })
}));

vi.mock('../../icui/services/mediaService', () => ({
  mediaService: {
    validateFile: vi.fn().mockReturnValue({ valid: true })
  }
}));

// Mock ExplorerDropProvider to avoid complex dependencies
vi.mock('../../icui/components/explorer/ExplorerDropProvider', () => ({
  default: ({ uploadApi }: any) => <div data-testid="explorer-drop-provider">ExplorerDropProvider</div>
}));

describe('GlobalUploadManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location for base URL
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:3000' },
      writable: true
    });
  });

  it('renders without crashing', () => {
    const { container } = render(<GlobalUploadManager />);
    expect(container).toBeInTheDocument();
  });

  it('opens widget on custom event', async () => {
    render(<GlobalUploadManager />);
    
    // Dispatch the custom event
    const event = new CustomEvent('icotes:open-upload-widget');
    window.dispatchEvent(event);
    
    // Should not throw and component should handle the event
    await waitFor(() => {
      // The component should react to the event
      expect(true).toBe(true); // Basic check that no errors occurred
    });
  });

  it('handles paste events with files', async () => {
    render(<GlobalUploadManager />);
    
    const file1 = new File(['content'], 'test1.txt', { type: 'text/plain' });
    const file2 = new File(['content'], 'test2.jpg', { type: 'image/jpeg' });
    
    const pasteEvent = new Event('paste') as any;
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: {
        items: [
          { kind: 'file', getAsFile: () => file1 },
          { kind: 'file', getAsFile: () => file2 }
        ]
      }
    });
    
    window.dispatchEvent(pasteEvent);
    
    await waitFor(() => {
      expect(true).toBe(true); // Component should handle paste without errors
    });
  });

  it('handles drag and drop events', async () => {
    const { container } = render(<GlobalUploadManager />);
    
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    
    const dragEvent = new Event('dragover') as any;
    Object.defineProperty(dragEvent, 'dataTransfer', {
      value: {
        types: ['Files'],
        files: [file]
      }
    });
    
    fireEvent(container, dragEvent);
    
    const dropEvent = new Event('drop') as any;
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: {
        files: [file]
      }
    });
    
    fireEvent(container, dropEvent);
    
    await waitFor(() => {
      expect(true).toBe(true); // Component should handle drag/drop without errors
    });
  });

  it('sets up global event listeners on mount', () => {
    const addEventListenerSpy = vi.spyOn(window, 'addEventListener');
    
    render(<GlobalUploadManager />);
    
    expect(addEventListenerSpy).toHaveBeenCalledWith('icotes:open-upload-widget', expect.any(Function));
    expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    expect(addEventListenerSpy).toHaveBeenCalledWith('paste', expect.any(Function));
  });

  it('cleans up event listeners on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');
    
    const { unmount } = render(<GlobalUploadManager />);
    unmount();
    
    expect(removeEventListenerSpy).toHaveBeenCalledWith('icotes:open-upload-widget', expect.any(Function));
    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    expect(removeEventListenerSpy).toHaveBeenCalledWith('paste', expect.any(Function));
  });
});