import { useCallback, useRef, useState } from 'react';
import { backendService, ICUIFileNode } from '../../services';
import { getParentDirectoryPath, joinPathSegments } from './pathUtils';
import { log } from '../../../services/frontend-logger';

type LoadRef = React.MutableRefObject<((path: string, opts?: { force?: boolean }) => Promise<void>) | undefined>;

export function useExplorerRename(params: {
  flattenedFiles: ICUIFileNode[];
  loadDirectoryRef: LoadRef;
  currentPath: string;
  onFileRename?: (oldPath: string, newPath: string) => void;
  setError: (msg: string | null) => void;
}) {
  const { flattenedFiles, loadDirectoryRef, currentPath, onFileRename, setError } = params;

  const [renamingFileId, setRenamingFileId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const renameInputRef = useRef<HTMLInputElement>(null);

  const startRename = useCallback((file: ICUIFileNode) => {
    setRenamingFileId(file.path);
    setRenameValue(file.name);
    setTimeout(() => {
      if (renameInputRef.current) {
        renameInputRef.current.focus();
        renameInputRef.current.select();
      }
    }, 0);
  }, []);

  const cancelRename = useCallback(() => {
    setRenamingFileId(null);
    setRenameValue('');
  }, []);

  const confirmRename = useCallback(async () => {
    if (!renamingFileId || !renameValue.trim()) {
      cancelRename();
      return;
    }

    const file = flattenedFiles.find(f => f.path === renamingFileId);
    if (!file || renameValue.trim() === file.name) {
      cancelRename();
      return;
    }

    try {
      const parentPath = getParentDirectoryPath(file.path);
      const newPath = joinPathSegments(parentPath, renameValue.trim());
      if (newPath === file.path) {
        cancelRename();
        return;
      }

      await backendService.moveFile(file.path, newPath);
      await loadDirectoryRef.current?.(currentPath, { force: true });
      onFileRename?.(file.path, newPath);
      log.info('ICUIEnhancedExplorer', 'Renamed file inline', { oldPath: file.path, newPath });
    } catch (error) {
      log.error('ICUIEnhancedExplorer', 'Failed to rename file inline', { oldPath: renamingFileId, newName: renameValue, error });
      setError(error instanceof Error ? error.message : 'Failed to rename file');
    } finally {
      cancelRename();
    }
  }, [renamingFileId, renameValue, flattenedFiles, cancelRename, currentPath, onFileRename, loadDirectoryRef, setError]);

  const handleRenameKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      confirmRename();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancelRename();
    }
  }, [confirmRename, cancelRename]);

  return {
    renamingFileId,
    renameValue,
    renameInputRef,
    startRename,
    cancelRename,
    confirmRename,
    handleRenameKeyDown,
    setRenameValue,
  } as const;
}
