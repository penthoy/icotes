import { useCallback } from 'react';
import { ICUI_FILE_LIST_MIME, useExplorerFileDrag } from '../../lib/dnd';
import type { ICUIFileNode } from '../../services';

export function useExplorerDnD(params: {
  selectedItems: ICUIFileNode[];
  isSelected: (id: string) => boolean;
}) {
  const { selectedItems, isSelected } = params;

  const { getDragProps } = useExplorerFileDrag({
    getSelection: () => selectedItems.map(f => ({ path: f.path, name: f.name, type: f.type })),
    isItemSelected: (id: string) => isSelected(id),
    toDescriptor: (node: ICUIFileNode) => ({ path: node.path, name: node.name, type: node.type }),
  });

  const isInternalExplorerDrag = useCallback((event: React.DragEvent) => {
    try {
      const types = event.dataTransfer?.types as any;
      if (!types) return false;
      for (let i = 0; i < types.length; i++) {
        if (types[i] === ICUI_FILE_LIST_MIME) return true;
      }
      return false;
    } catch {
      return false;
    }
  }, []);

  return { getDragProps, isInternalExplorerDrag };
}
