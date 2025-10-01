import { describe, it, expect } from 'vitest';
import { flattenVisibleTree, buildNodeMapByPath, createAnnotateWithExpansion, applyChildrenResults, findNodeInTree } from '../../../src/icui/components/explorer/utils';

type Node = {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: Node[];
  isExpanded?: boolean;
};

const sampleTree: Node[] = [
  { id: 'f', name: 'folder', type: 'folder', path: '/folder', isExpanded: true, children: [
    { id: 'a', name: 'a.txt', type: 'file', path: '/folder/a.txt' },
    { id: 'sub', name: 'sub', type: 'folder', path: '/folder/sub', isExpanded: false, children: [
      { id: 'b', name: 'b.txt', type: 'file', path: '/folder/sub/b.txt' },
    ]},
  ]},
  { id: 'c', name: 'c.txt', type: 'file', path: '/c.txt' },
];

describe('explorer utils', () => {
  it('flattens only visible nodes', () => {
    const flat = flattenVisibleTree(sampleTree as any);
    const names = flat.map(n => n.name);
    expect(names).toEqual(['folder', 'a.txt', 'sub', 'c.txt']);
  });

  it('builds node map by path', () => {
    const map = buildNodeMapByPath(sampleTree as any);
    expect(map.get('/folder')?.name).toBe('folder');
    expect(map.get('/c.txt')?.name).toBe('c.txt');
  });

  it('annotates with expansion flags and reuses children', () => {
    const expanded = new Set<string>(['/folder', '/folder/sub']);
    const annotate = createAnnotateWithExpansion(expanded);
    const prev = buildNodeMapByPath(sampleTree as any);
    const annotated = annotate([{ id: 'folder', name: 'folder', type: 'folder', path: '/folder', children: [] } as any], prev);
    expect((annotated[0] as any).isExpanded).toBe(true);
  });

  it('applies children results into current tree', () => {
    const expanded = new Set<string>(['/folder']);
    const annotate = createAnnotateWithExpansion(expanded);
    const prev = buildNodeMapByPath(sampleTree as any);
    const updated = applyChildrenResults(sampleTree as any, [{ path: '/folder', children: [{ id: 'x', name: 'x.txt', type: 'file', path: '/folder/x.txt' } as any] }], prev, annotate);
    const map = buildNodeMapByPath(updated as any);
    expect(map.get('/folder/x.txt')?.name).toBe('x.txt');
  });

  it('finds node by id', () => {
    const found = findNodeInTree(sampleTree as any, 'b');
    expect(found?.path).toBe('/folder/sub/b.txt');
  });
});
