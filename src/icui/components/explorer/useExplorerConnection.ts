import { useEffect } from 'react';
import { backendService } from '../../services';
import { log } from '../../../services/frontend-logger';

const DEBUG_EXPLORER = import.meta.env?.VITE_DEBUG_EXPLORER === 'true';

export interface UseExplorerConnectionParams {
  currentPath: string;
  loadDirectory: (path: string, opts?: { force?: boolean }) => Promise<void>;
  loadDirectoryRef: React.MutableRefObject<((path: string, opts?: { force?: boolean }) => Promise<void>) | undefined>;
  checkConnection: () => Promise<boolean>;
  setIsConnected: (v: boolean) => void;
}

export function useExplorerConnection({
  currentPath,
  loadDirectory,
  loadDirectoryRef,
  checkConnection,
  setIsConnected,
}: UseExplorerConnectionParams) {
  useEffect(() => {
    let mounted = true;
    if (DEBUG_EXPLORER) {
      console.debug('[ICUIExplorer][mount] effect start', { currentPath });
    }
    const handleConnectionChange = (payload: any) => {
      if (!mounted) return;
      const connected = payload.status === 'connected';
      setIsConnected(connected);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][event] connection_status_changed', { connected });
      }
      if (connected) {
        // Perform (or re-perform) directory load now that we're connected
        loadDirectoryRef.current ? loadDirectoryRef.current(currentPath, { force: true }) : loadDirectory(currentPath, { force: true });
      }
    };

    backendService.on('connection_status_changed', handleConnectionChange);

    // Kick off connection check AFTER listener is attached so we don't miss the first event
    (async () => {
      const status = await checkConnection();
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][mount] initial checkConnection result', { status });
      }
      if (status) {
        // If already connected, load immediately
        loadDirectory(currentPath, { force: true });
      } else {
        // Not yet connected: calling getConnectionStatus() again will trigger ensureInitialized -> connection attempt
        try {
          if (DEBUG_EXPLORER) {
            console.debug('[ICUIExplorer][mount] triggering second status call to start connection');
          }
          await backendService.getConnectionStatus();
        } catch {/* ignore */}
      }
    })();

    return () => {
      mounted = false;
      backendService.off('connection_status_changed', handleConnectionChange);
      if (DEBUG_EXPLORER) {
        console.debug('[ICUIExplorer][unmount] cleanup');
      }
    };
  }, [currentPath, loadDirectory, loadDirectoryRef, checkConnection, setIsConnected]);
}
