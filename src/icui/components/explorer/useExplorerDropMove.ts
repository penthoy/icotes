import { useCallback, useRef } from 'react';
import { ICUIFileNode } from '../../services';
import { ICUI_FILE_LIST_MIME, isExplorerPayload } from '../../lib/dnd';
import { getParentDirectoryPath, normalizeDirPath } from './pathUtils';
import { planExplorerMoveOperations } from './movePlanner';
import { log } from '../../../services/frontend-logger';
import { backendService } from '../../services';

export function useExplorerDropMove(params: {
  currentPath: string;
  isInternalExplorerDrag: (e: React.DragEvent) => boolean;
  handleRefresh: () => Promise<void>;
  clearSelection: () => void;
  setError: (msg: string | null) => void;
  clearDragHoverState: () => void;
}) {
  const { currentPath, isInternalExplorerDrag, handleRefresh, clearSelection, setError, clearDragHoverState } = params;
  const dragOperationRef = useRef(false);

  const handleInternalDrop = useCallback(async (event: React.DragEvent, targetNode?: ICUIFileNode | null) => {
    if (!isInternalExplorerDrag(event)) return;

    event.preventDefault();
    event.stopPropagation();

    const traceId = (event.dataTransfer as any)._icuiTraceId || `drop-${Date.now().toString(36)}`;
    try {
      log.info('ExplorerDnD', '[DND][drop:init]', {
        traceId,
        targetNode: targetNode ? { path: targetNode.path, type: targetNode.type } : null,
        currentPath,
      });
    } catch {}

    const transfer = event.dataTransfer;
    const rawPayload = transfer?.getData(ICUI_FILE_LIST_MIME);
    if (!rawPayload) {
      clearDragHoverState();
      return;
    }

    let payload: any;
    try {
      payload = JSON.parse(rawPayload);
    } catch (parseError) {
      console.error('ICUIEnhancedExplorer', 'Failed to parse drag payload', parseError);
      clearDragHoverState();
      return;
    }

    if (!isExplorerPayload(payload)) {
      clearDragHoverState();
      return;
    }

    const destinationDirRaw = targetNode
      ? (targetNode.type === 'folder' ? targetNode.path : getParentDirectoryPath(targetNode.path))
      : currentPath;
    const destinationDir = normalizeDirPath(destinationDirRaw);

    const descriptors = payload.items ?? payload.paths.map((path: string, index: number) => ({
      path,
      name: path.split('/').pop() || `item-${index}`,
      type: 'file' as const,
    }));

    let plannedOperations: { source: string; destination: string }[] = [];
    let skipped: string[] = [];
    try {
      const planning = planExplorerMoveOperations({ descriptors, destinationDir });
      plannedOperations = planning.operations;
      skipped = planning.skipped;
      log.info('ExplorerDnD', '[DND][drop:plan]', {
        traceId,
        destinationDir,
        operations: plannedOperations,
        skipped,
      });
    } catch (planError) {
      log.error('ExplorerDnD', '[DND][drop:plan:error]', { traceId, error: planError });
      setError(planError instanceof Error ? planError.message : 'Failed to plan move');
      clearDragHoverState();
      return;
    }

    if (plannedOperations.length === 0) {
      clearDragHoverState();
      return;
    }

    dragOperationRef.current = true;
    try {
      log.info('ExplorerDnD', '[DND][drop:validate:start]', { traceId, destinationDir });
      const directorySnapshot = await backendService.getDirectoryContents(destinationDir, true).catch(() => [] as ICUIFileNode[]);
      const existingNames = new Set(directorySnapshot.map(node => node.name));

      for (const op of plannedOperations) {
        const basename = op.destination.split('/').pop() || '';
        if (existingNames.has(basename)) {
          log.warn('ExplorerDnD', '[DND][drop:validate:conflict]', { traceId, basename });
          throw new Error(`Cannot move “${basename}”: destination already contains an item with the same name.`);
        }
      }

      for (const op of plannedOperations) {
        log.info('ExplorerDnD', '[DND][drop:execute]', { traceId, op });
        await backendService.moveFile(op.source, op.destination);
      }

      await handleRefresh();
      clearSelection();
      setError(null);
      log.info('ExplorerDnD', '[DND][drop:complete]', { traceId, moved: plannedOperations.length, skipped });
    } catch (error) {
      console.error('ICUIEnhancedExplorer', 'Failed to move selection', error);
      log.error('ExplorerDnD', '[DND][drop:failure]', { traceId, error });
      setError(error instanceof Error ? error.message : 'Failed to move files');
    } finally {
      dragOperationRef.current = false;
      clearDragHoverState();
    }

    if (skipped.length > 0) {
      log.warn('ICUIEnhancedExplorer', 'Skipped moving some paths due to invalid targets', { traceId, skipped });
    }
  }, [isInternalExplorerDrag, currentPath, clearDragHoverState, handleRefresh, clearSelection, setError]);

  return { handleInternalDrop } as const;
}
