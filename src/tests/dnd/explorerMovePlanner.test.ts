import { describe, expect, it } from 'vitest';
import { planExplorerMoveOperations } from '../../icui/components/explorer/movePlanner';

const makeDescriptor = (path: string, name: string, type: 'file' | 'folder' = 'file') => ({
  path,
  name,
  type,
});

describe('planExplorerMoveOperations', () => {
  it('ignores ancestor directories when a descendant is also selected', () => {
    const { operations, skipped } = planExplorerMoveOperations({
      descriptors: [
        makeDescriptor('/workspace/test2', 'test2', 'folder'),
        makeDescriptor('/workspace/test2/test', 'test', 'folder'),
      ],
      destinationDir: '/workspace/test3',
    });

    expect(operations).toEqual([
      {
        source: '/workspace/test2/test',
        destination: '/workspace/test3/test',
      },
    ]);
    expect(skipped).toContain('/workspace/test2');
  });

  it('returns no operations when dropping into the same parent directory', () => {
    const { operations, skipped } = planExplorerMoveOperations({
      descriptors: [makeDescriptor('/workspace/test2/test', 'test', 'file')],
      destinationDir: '/workspace/test2',
    });

    expect(operations).toHaveLength(0);
    expect(skipped).toContain('/workspace/test2/test');
  });

  it('rejects moves into a descendant of the source', () => {
    const { operations, skipped } = planExplorerMoveOperations({
      descriptors: [makeDescriptor('/workspace/test', 'test', 'folder')],
      destinationDir: '/workspace/test/testf',
    });

    expect(operations).toHaveLength(0);
    expect(skipped).toContain('/workspace/test');
  });
});
