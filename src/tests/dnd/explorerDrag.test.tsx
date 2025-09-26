import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { useExplorerFileDrag } from '../../icui/lib/dnd/hooks';

// Minimal stand‑in for ICUIFileNode
interface NodeLike { id: string; path: string; name: string; type: 'file' | 'folder'; }

function TestDraggable({ nodes, selected }: { nodes: NodeLike[]; selected: string[] }) {
  const { getDragProps } = useExplorerFileDrag({
    getSelection: () => nodes.filter(n => selected.includes(n.id)).map(n => ({ path: n.path, name: n.name, type: n.type })),
    isItemSelected: (id: string) => selected.includes(id),
    toDescriptor: (n: NodeLike) => ({ path: n.path, name: n.name, type: n.type })
  });

  return (
    <div>
      {nodes.map(n => (
        <div key={n.id} data-testid={`item-${n.id}`} {...getDragProps(n)}>{n.name}</div>
      ))}
    </div>
  );
}

describe('Explorer drag foundation', () => {
  it('serializes multi-selection into DataTransfer', () => {
    const nodes: NodeLike[] = [
      { id: '1', path: '/a.txt', name: 'a.txt', type: 'file' },
      { id: '2', path: '/b.txt', name: 'b.txt', type: 'file' },
    ];
    const { getByTestId } = render(<TestDraggable nodes={nodes} selected={['1','2']} />);

    const target = getByTestId('item-1');
    const setDataMock: Record<string,string> = {};
    const dataTransfer: any = {
      setData: (type: string, data: string) => { setDataMock[type] = data; },
      effectAllowed: ''
    };

    fireEvent.dragStart(target, { dataTransfer });
    expect(Object.keys(setDataMock).length).toBeGreaterThan(0);
    const custom = setDataMock['application/x-icui-file-list'];
    expect(custom).toBeTruthy();
    const parsed = JSON.parse(custom);
    expect(parsed.paths).toEqual(['/a.txt','/b.txt']);
    expect(parsed.multi).toBe(true);
  });

  it('uses single item when origin not in selection', () => {
    const nodes: NodeLike[] = [
      { id: '1', path: '/a.txt', name: 'a.txt', type: 'file' },
      { id: '2', path: '/b.txt', name: 'b.txt', type: 'file' },
    ];
    const { getByTestId } = render(<TestDraggable nodes={nodes} selected={['2']} />);

    const target = getByTestId('item-1'); // not selected
    const setDataMock: Record<string,string> = {};
    const dataTransfer: any = {
      setData: (type: string, data: string) => { setDataMock[type] = data; },
      effectAllowed: ''
    };
    fireEvent.dragStart(target, { dataTransfer });
    const custom = setDataMock['application/x-icui-file-list'];
    const parsed = JSON.parse(custom);
    expect(parsed.paths).toEqual(['/a.txt']);
    expect(parsed.multi).toBe(false);
  });
});
