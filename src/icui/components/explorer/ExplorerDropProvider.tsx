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
    console.log('[ExplorerDropProvider] Initializing with selector:', selector);
    
    let cleanup: (() => void) | null = null;
    let retryCount = 0;
    const maxRetries = 10;
    
    const trySetup = () => {
      const root = document.querySelector(selector) as HTMLElement | null;
      
      if (!root) {
        retryCount++;
        if (retryCount <= maxRetries) {
          console.log(`[ExplorerDropProvider] Root element not found (attempt ${retryCount}/${maxRetries}), retrying in 100ms...`);
          setTimeout(trySetup, 100);
          return;
        } else {
          console.error('[ExplorerDropProvider] Root element not found after max retries for selector:', selector);
          console.log('[ExplorerDropProvider] Available elements with data attributes:', 
            Array.from(document.querySelectorAll('[data-*]')).map(el => ({
              element: el,
              dataset: (el as HTMLElement).dataset
            }))
          );
          return;
        }
      }
      
      console.log('[ExplorerDropProvider] Root element found:', root, 'selector:', selector);
      console.log('[ExplorerDropProvider] Root element dataset:', root.dataset);
      console.log('[ExplorerDropProvider] Root element classes:', root.className);
      console.log('[ExplorerDropProvider] Root element children count:', root.children.length);
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
      console.log('[ExplorerDropProvider] DRAGOVER event fired, target:', e.target);
      if (!e.dataTransfer) {
        console.warn('[ExplorerDropProvider] No dataTransfer in dragover');
        return;
      }
      console.log('[ExplorerDropProvider] dragover event types:', e.dataTransfer.types);
      if (!Array.from(e.dataTransfer.types).includes('Files')) {
        console.log('[ExplorerDropProvider] No Files type in dragover, ignoring');
        return;
      }
      e.preventDefault();
      console.log('[ExplorerDropProvider] dragover Files detected, highlighting root');
      ensureRootHighlight();
      const item = findItem(e.target);
      console.log('[ExplorerDropProvider] Found item from target:', item);
      if (item && item !== hoverEl) {
        // Remove highlights from any previously highlighted elements (defensive multi-hover cleanup)
        if (hoverEl) hoverEl.classList.remove('ring', 'ring-blue-400');
        // Also sweep any accidental leftovers
        root.querySelectorAll('.ring.ring-blue-400').forEach(el => {
          if (el !== item) el.classList.remove('ring', 'ring-blue-400');
        });
        hoverEl = item;
        item.classList.add('ring', 'ring-blue-400');
        console.log('[ExplorerDropProvider] Highlighted item:', item);
      }
    };
    const clearHover = () => {
      if (hoverEl) {
        hoverEl.classList.remove('ring', 'ring-blue-400');
        hoverEl = null;
      }
    };
    const onDragEnter = (e: DragEvent) => {
      console.log('[ExplorerDropProvider] DRAGENTER event fired, target:', e.target);
      if (!e.dataTransfer) {
        console.warn('[ExplorerDropProvider] No dataTransfer in dragenter');
        return;
      }
      console.log('[ExplorerDropProvider] dragenter event types:', e.dataTransfer.types);
      if (!Array.from(e.dataTransfer.types).includes('Files')) {
        console.log('[ExplorerDropProvider] No Files type in dragenter, ignoring');
        return;
      }
      console.log('[ExplorerDropProvider] dragenter Files detected, highlighting root');
      ensureRootHighlight();
    };

    const onDrop = (e: DragEvent) => {
      console.log('[ExplorerDropProvider] DROP EVENT FIRED!', e);
      console.log('[ExplorerDropProvider] Drop dataTransfer:', e.dataTransfer);
      console.log('[ExplorerDropProvider] Drop dataTransfer types:', e.dataTransfer?.types);
      console.log('[ExplorerDropProvider] Drop target:', e.target);
      
      if (!e.dataTransfer) {
        console.warn('[ExplorerDropProvider] No dataTransfer in drop event');
        return;
      }
      
      if (!Array.from(e.dataTransfer.types).includes('Files')) {
        console.warn('[ExplorerDropProvider] No Files type in drop dataTransfer types:', e.dataTransfer.types);
        return;
      }
      
      console.log('[ExplorerDropProvider] Files type detected, preventing default and processing...');
      e.preventDefault();
      
      const files = Array.from(e.dataTransfer.files);
      console.log('[ExplorerDropProvider] Files from drop:', files);
      
      const item = findItem(e.target);
      console.log('[ExplorerDropProvider] Found drop target item:', item);
      
      const rootEl = root; // captured from outer scope
      let targetPath = defaultDir;
      
      if (item) {
        targetPath = item.getAttribute(itemAttr) || defaultDir;
        console.log('[ExplorerDropProvider] Dropping onto item, target path:', targetPath);
      } else if (rootEl) {
        // Fallback to current explorer path (unlocked view) so dropping into blank area uses visible directory
        const current = rootEl.getAttribute('data-current-path');
        if (current) {
          targetPath = current;
          console.log('[ExplorerDropProvider] Using current explorer path:', targetPath);
        } else {
          console.log('[ExplorerDropProvider] No current path on root, using default:', defaultDir);
        }
      }
      
      const workspaceRoot = (() => { try { return getWorkspaceRoot(); } catch { return '/'; } })();
      console.log('[ExplorerDropProvider] Workspace root:', workspaceRoot);
      
      // If targetPath is relative (doesn't start with /), make it absolute under workspaceRoot
      if (!targetPath.startsWith('/')) {
        targetPath = `${workspaceRoot.replace(/\/$/, '')}/${targetPath}`.replace(/\/+/, '/');
        console.log('[ExplorerDropProvider] Made target path absolute:', targetPath);
      }
      
      // If targetPath is a directory (ends with /) ensure no duplicate slash after join
      const isDirDrop = targetPath.endsWith('/') || targetPath.split('/').pop() === '';
      console.log('[ExplorerDropProvider] Is directory drop:', isDirDrop);
      
      // If the user dropped multiple files, request opening the Upload widget for visibility
      if (files.length > 1) {
        console.log('[ExplorerDropProvider] Multiple files, opening upload widget');
        window.dispatchEvent(new CustomEvent('icotes:open-upload-widget'));
      }

      files.forEach(file => {
        const finalDestDir = isDirDrop || targetPath.endsWith('/') ? targetPath.replace(/\/$/, '') : targetPath;
        // If dropping onto a file node, we interpret as its parent directory
        const effectiveDir = finalDestDir && !finalDestDir.endsWith(file.name) && !finalDestDir.includes('.')
          ? finalDestDir
          : finalDestDir.replace(/\/[^/]+$/, '');
        const absDestPath = `${effectiveDir}/${file.name}`.replace(/\/+/, '/');
        console.log('[ExplorerDropProvider] Processing file:', file.name, 'to path:', absDestPath);
        // Send absolute path directly; backend will validate it resides within workspace root.
        uploadApi.addFiles([file], { context: 'explorer', destPath: absDestPath });
      });
      
      console.log('[ExplorerDropProvider] Drop processing complete, clearing highlights');
      clearHover();
      clearRootHighlight();
      setTimeout(() => clearHover(), 0); // microtask ensure styles removed
    };
    const onDragLeave = (e: DragEvent) => {
      console.log('[ExplorerDropProvider] DRAGLEAVE event fired, target:', e.target, 'relatedTarget:', e.relatedTarget);
      if (!(e.relatedTarget instanceof HTMLElement)) {
        console.log('[ExplorerDropProvider] External drag leave detected, clearing hover');
        clearHover();
        // Use bounding box heuristic for external drags leaving window (relatedTarget null)
        if (e.target === root) {
          console.log('[ExplorerDropProvider] Drag left root element, clearing root highlight');
          clearRootHighlight();
        }
      } else {
        console.log('[ExplorerDropProvider] Internal drag leave, related target is HTML element');
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
      
      cleanup = () => {
        root.removeEventListener('dragover', onDragOver);
        root.removeEventListener('dragenter', onDragEnter);
        root.removeEventListener('drop', onDrop);
        root.removeEventListener('dragleave', onDragLeave);
        window.removeEventListener('dragend', forceClear);
        window.removeEventListener('mouseup', forceClear);
        window.removeEventListener('drop', forceClear, true);
      };
    };
    
    trySetup();
    
    return () => {
      if (cleanup) cleanup();
    };
  }, [selector, itemAttr, uploadApi, defaultDir]);

  return null;
}

export default ExplorerDropProvider;