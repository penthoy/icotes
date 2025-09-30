import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useComposerDnd } from '../../icui/components/chat/hooks/useComposerDnd';
import { ICUI_FILE_LIST_MIME } from '../../icui/lib/dnd';

// Mock DOM element for testing
const createMockElement = () => {
  const element = document.createElement('div');
  element.addEventListener = vi.fn();
  element.removeEventListener = vi.fn();
  element.contains = vi.fn();
  return element;
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useComposerDnd hook', () => {
  it('sets up event listeners on mount', () => {
    const mockElement = createMockElement();
    const mockOpts = {
      setActive: vi.fn(),
      onRefs: vi.fn(),
      onFiles: vi.fn()
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    expect(mockElement.addEventListener).toHaveBeenCalledWith('dragover', expect.any(Function));
    expect(mockElement.addEventListener).toHaveBeenCalledWith('dragleave', expect.any(Function));
    expect(mockElement.addEventListener).toHaveBeenCalledWith('drop', expect.any(Function));
  });

  it('handles dragover with explorer payload', () => {
    const mockElement = createMockElement();
    const setActive = vi.fn();
    const mockOpts = {
      setActive,
      onRefs: vi.fn(),
      onFiles: vi.fn()
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    // Get the dragover handler from addEventListener calls
    const dragOverHandler = (mockElement.addEventListener as any).mock.calls
      .find((call: any) => call[0] === 'dragover')?.[1];

    const mockEvent = {
      dataTransfer: {
        types: [ICUI_FILE_LIST_MIME]
      },
      preventDefault: vi.fn()
    };

    dragOverHandler(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(setActive).toHaveBeenCalledWith(true);
  });

  it('handles dragover with files', () => {
    const mockElement = createMockElement();
    const setActive = vi.fn();
    const mockOpts = {
      setActive,
      onRefs: vi.fn(),
      onFiles: vi.fn()
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    const dragOverHandler = (mockElement.addEventListener as any).mock.calls
      .find((call: any) => call[0] === 'dragover')?.[1];

    const mockEvent = {
      dataTransfer: {
        types: ['Files']
      },
      preventDefault: vi.fn()
    };

    dragOverHandler(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(setActive).toHaveBeenCalledWith(true);
  });

  it('handles drop with explorer payload', () => {
    const mockElement = createMockElement();
    const onRefs = vi.fn();
    const mockOpts = {
      setActive: vi.fn(),
      onRefs,
      onFiles: vi.fn()
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    const dropHandler = (mockElement.addEventListener as any).mock.calls
      .find((call: any) => call[0] === 'drop')?.[1];

    const explorerPayload = {
      kind: 'file',
      paths: ['/test/file1.txt', '/test/file2.js'],
      items: [
        { type: 'file', path: '/test/file1.txt', name: 'file1.txt' },
        { type: 'file', path: '/test/file2.js', name: 'file2.js' }
      ],
      multi: true,
      ts: Date.now()
    };

    const mockEvent = {
      dataTransfer: {
        types: [ICUI_FILE_LIST_MIME],
        getData: vi.fn().mockReturnValue(JSON.stringify(explorerPayload))
      },
      preventDefault: vi.fn()
    };

    dropHandler(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(onRefs).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          path: '/test/file1.txt',
          name: 'file1.txt',
          kind: 'file'
        }),
        expect.objectContaining({
          path: '/test/file2.js',
          name: 'file2.js',
          kind: 'file'
        })
      ])
    );
  });

  it('handles drop with OS files', () => {
    const mockElement = createMockElement();
    const onFiles = vi.fn();
    const mockOpts = {
      setActive: vi.fn(),
      onRefs: vi.fn(),
      onFiles
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    const dropHandler = (mockElement.addEventListener as any).mock.calls
      .find((call: any) => call[0] === 'drop')?.[1];

    const file1 = new File(['content1'], 'test1.txt', { type: 'text/plain' });
    const file2 = new File(['content2'], 'test2.js', { type: 'text/javascript' });

    const mockEvent = {
      dataTransfer: {
        getData: vi.fn().mockReturnValue(''), // No explorer payload
        files: [file1, file2]
      },
      preventDefault: vi.fn()
    };

    dropHandler(mockEvent);

    expect(mockEvent.preventDefault).toHaveBeenCalled();
    expect(onFiles).toHaveBeenCalledWith([file1, file2]);
  });

  it('ignores invalid explorer payloads', () => {
    const mockElement = createMockElement();
    const onRefs = vi.fn();
    const mockOpts = {
      setActive: vi.fn(),
      onRefs,
      onFiles: vi.fn()
    };

    renderHook(() => useComposerDnd(mockElement, mockOpts));

    const dropHandler = (mockElement.addEventListener as any).mock.calls
      .find((call: any) => call[0] === 'drop')?.[1];

    const mockEvent = {
      dataTransfer: {
        getData: vi.fn().mockReturnValue('invalid json')
      },
      preventDefault: vi.fn()
    };

    dropHandler(mockEvent);

    expect(onRefs).not.toHaveBeenCalled();
  });

  it('cleans up event listeners on unmount', () => {
    const mockElement = createMockElement();
    const mockOpts = {
      setActive: vi.fn(),
      onRefs: vi.fn(),
      onFiles: vi.fn()
    };

    const { unmount } = renderHook(() => useComposerDnd(mockElement, mockOpts));

    unmount();

    expect(mockElement.removeEventListener).toHaveBeenCalledWith('dragover', expect.any(Function));
    expect(mockElement.removeEventListener).toHaveBeenCalledWith('dragleave', expect.any(Function));
    expect(mockElement.removeEventListener).toHaveBeenCalledWith('drop', expect.any(Function));
  });

  it('handles null element gracefully', () => {
    const mockOpts = {
      setActive: vi.fn(),
      onRefs: vi.fn(),
      onFiles: vi.fn()
    };

    // Should not throw when element is null
    expect(() => {
      renderHook(() => useComposerDnd(null, mockOpts));
    }).not.toThrow();
  });
});