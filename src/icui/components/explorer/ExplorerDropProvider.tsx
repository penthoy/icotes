import React, { useEffect } from 'react';
import { getWorkspaceRoot } from '../../lib/workspaceUtils';
import { useMediaUpload } from '../../hooks/useMediaUpload';

interface Props {
  selector?: string; // container that holds explorer items
  itemAttr?: string; // attribute on item containing path
  uploadApi: ReturnType<typeof useMediaUpload>;
  defaultDir?: string; // fallback directory
}

/**
 * ExplorerDropProvider
 * Adds dragover/drop handling for explorer items that have a data-path attribute.
 */
export function ExplorerDropProvider({ selector = '[data-explorer-root]', itemAttr = 'data-path', uploadApi, defaultDir = '.' }: Props) {
  useEffect(() => {
    const root = document.querySelector(selector) as HTMLElement | null;
    if (!root) return;
    root.dataset.dropScope = 'explorer';

    let hoverEl: HTMLElement | null = null;

    const findItem = (target: EventTarget | null): HTMLElement | null => {
      if (!(target instanceof HTMLElement)) return null;
      return target.closest(`[${itemAttr}]`) as HTMLElement | null;
    };

    const onDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (!Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      const item = findItem(e.target);
      if (hoverEl && hoverEl !== item) hoverEl.classList.remove('ring', 'ring-blue-400');
      if (item) {
        hoverEl = item;
        item.classList.add('ring', 'ring-blue-400');
      }
    };
    const onDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (!Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files);
      const item = findItem(e.target);
      let targetPath = defaultDir;
      if (item) {
        targetPath = item.getAttribute(itemAttr) || defaultDir;
      }
      
      // DEBUG: Print exactly where we're dropping
      console.log('🎯 [DROP DEBUG] Raw drop info:', {
        targetPath,
        defaultDir,
        itemAttr,
        hasItem: !!item,
        itemPath: item?.getAttribute(itemAttr),
        files: files.map(f => f.name)
      });
      
      // Normalize path: if absolute and starts with workspace root, make it relative
      const workspaceRoot = (() => { try { return getWorkspaceRoot(); } catch { return '/'; } })();
      if (targetPath.startsWith(workspaceRoot)) {
        targetPath = targetPath.substring(workspaceRoot.length).replace(/^\//, '');
      }
      
      // Clean up relative path markers
      targetPath = targetPath.replace(/^\.\/?/, '');
      if (targetPath === '.' || targetPath === '') targetPath = '';
      
      console.log('🎯 [DROP DEBUG] Processed paths:', {
        workspaceRoot,
        targetPath,
        willCreateDestPath: targetPath ? `${targetPath.replace(/\/$/, '')}/${files[0]?.name}` : files[0]?.name
      });
      
      files.forEach(file => {
        const destPath = targetPath ? `${targetPath.replace(/\/$/, '')}/${file.name}` : file.name;
        console.log('🎯 [DROP DEBUG] Final destPath for', file.name, ':', destPath);
        uploadApi.addFiles([file], { context: 'explorer', destPath });
      });
      if (hoverEl) hoverEl.classList.remove('ring', 'ring-blue-400');
    };
    const onDragLeave = (e: DragEvent) => {
      if (!(e.relatedTarget instanceof HTMLElement)) {
        if (hoverEl) hoverEl.classList.remove('ring', 'ring-blue-400');
        hoverEl = null;
      }
    };

    root.addEventListener('dragover', onDragOver);
    root.addEventListener('drop', onDrop);
    root.addEventListener('dragleave', onDragLeave);
    return () => {
      root.removeEventListener('dragover', onDragOver);
      root.removeEventListener('drop', onDrop);
      root.removeEventListener('dragleave', onDragLeave);
    };
  }, [selector, itemAttr, uploadApi, defaultDir]);

  return null;
}

export default ExplorerDropProvider;