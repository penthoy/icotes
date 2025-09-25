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

    const ensureRootHighlight = () => {
      if (!root.classList.contains('ring-1')) {
        root.classList.add('ring-1','ring-blue-300');
      }
    };
    const clearRootHighlight = () => {
      root.classList.remove('ring-1','ring-blue-300');
    };

    const onDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (!Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      ensureRootHighlight();
      const item = findItem(e.target);
      if (item && item !== hoverEl) {
        // Remove highlights from any previously highlighted elements (defensive multi-hover cleanup)
        if (hoverEl) hoverEl.classList.remove('ring', 'ring-blue-400');
        // Also sweep any accidental leftovers
        root.querySelectorAll('.ring.ring-blue-400').forEach(el => {
          if (el !== item) el.classList.remove('ring', 'ring-blue-400');
        });
        hoverEl = item;
        item.classList.add('ring', 'ring-blue-400');
      }
    };
    const clearHover = () => {
      if (hoverEl) {
        hoverEl.classList.remove('ring', 'ring-blue-400');
        hoverEl = null;
      }
    };
    const onDragEnter = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (!Array.from(e.dataTransfer.types).includes('Files')) return;
      ensureRootHighlight();
    };

    const onDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      if (!Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      const files = Array.from(e.dataTransfer.files);
      const item = findItem(e.target);
      const rootEl = root; // captured from outer scope
      let targetPath = defaultDir;
      if (item) {
        targetPath = item.getAttribute(itemAttr) || defaultDir;
      } else if (rootEl) {
        // Fallback to current explorer path (unlocked view) so dropping into blank area uses visible directory
        const current = rootEl.getAttribute('data-current-path');
        if (current) targetPath = current;
      }
      const workspaceRoot = (() => { try { return getWorkspaceRoot(); } catch { return '/'; } })();
      // If targetPath is relative (doesn't start with /), make it absolute under workspaceRoot
      if (!targetPath.startsWith('/')) {
        targetPath = `${workspaceRoot.replace(/\/$/, '')}/${targetPath}`.replace(/\/+/, '/');
      }
      // If targetPath is a directory (ends with /) ensure no duplicate slash after join
      const isDirDrop = targetPath.endsWith('/') || targetPath.split('/').pop() === '';
      // If the user dropped multiple files, request opening the Upload widget for visibility
      if (files.length > 1) {
        window.dispatchEvent(new CustomEvent('icotes:open-upload-widget'));
      }

      files.forEach(file => {
        const finalDestDir = isDirDrop || targetPath.endsWith('/') ? targetPath.replace(/\/$/, '') : targetPath;
        // If dropping onto a file node, we interpret as its parent directory
        const effectiveDir = finalDestDir && !finalDestDir.endsWith(file.name) && !finalDestDir.includes('.')
          ? finalDestDir
          : finalDestDir.replace(/\/[^/]+$/, '');
        const absDestPath = `${effectiveDir}/${file.name}`.replace(/\/+/, '/');
        // Send absolute path directly; backend will validate it resides within workspace root.
        uploadApi.addFiles([file], { context: 'explorer', destPath: absDestPath });
      });
      clearHover();
      clearRootHighlight();
      setTimeout(() => clearHover(), 0); // microtask ensure styles removed
    };
    const onDragLeave = (e: DragEvent) => {
      if (!(e.relatedTarget instanceof HTMLElement)) {
        clearHover();
        // Use bounding box heuristic for external drags leaving window (relatedTarget null)
        if (e.target === root) {
          clearRootHighlight();
        }
      }
    };

    root.addEventListener('dragover', onDragOver);
    root.addEventListener('dragenter', onDragEnter);
    root.addEventListener('drop', onDrop);
    root.addEventListener('dragleave', onDragLeave);
    const forceClear = () => clearHover();
    window.addEventListener('dragend', forceClear);
    window.addEventListener('mouseup', forceClear);
    window.addEventListener('drop', forceClear, true);
    return () => {
      root.removeEventListener('dragover', onDragOver);
      root.removeEventListener('dragenter', onDragEnter);
  root.removeEventListener('drop', onDrop);
      root.removeEventListener('dragleave', onDragLeave);
      window.removeEventListener('dragend', forceClear);
      window.removeEventListener('mouseup', forceClear);
      window.removeEventListener('drop', forceClear, true);
    };
  }, [selector, itemAttr, uploadApi, defaultDir]);

  return null;
}

export default ExplorerDropProvider;