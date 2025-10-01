import { useEffect, useRef } from 'react';
import { backendService, ICUIFileNode } from '../../services';
import { log } from '../../../services/frontend-logger';

export interface UseExplorerFsWatcherParams {
  currentPath: string;
  onRefresh: () => void | Promise<void>;
  loadDirectoryRef: React.MutableRefObject<((path: string, opts?: { force?: boolean }) => Promise<void>) | undefined>;
}

export function useExplorerFsWatcher({ currentPath, onRefresh, loadDirectoryRef }: UseExplorerFsWatcherParams) {
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusHandlerRef = useRef<((payload: any) => Promise<void>) | null>(null);

  useEffect(() => {
    const handleFileSystemEvent = (eventData: any) => {
      log.debug('ICUIExplorer', '[EXPL] filesystem_event received', { event: eventData?.event, data: eventData?.data });
      if (!eventData?.data) return;

      const { event, data } = eventData;
      const paths = [eventData.path, data.file_path, data.path, data.dir_path, data.src_path, data.dest_path].filter(
        (p): p is string => typeof p === 'string' && p.length > 0
      );

      switch (event) {
        case 'fs.file_created':
        case 'fs.directory_created':
        case 'fs.file_deleted':
        case 'fs.file_moved':
        case 'fs.file_copied': {
          if (refreshTimeoutRef.current) clearTimeout(refreshTimeoutRef.current);
          // Debounce structural refreshes
          refreshTimeoutRef.current = setTimeout(() => {
            log.debug('ICUIExplorer', '[EXPL] triggering debounced refresh', { currentPath, paths });
            if (loadDirectoryRef.current) loadDirectoryRef.current(currentPath);
            refreshTimeoutRef.current = null;
          }, 300);
          break;
        }
        case 'fs.file_modified': {
          // Non-structural; ignore for tree refresh
          log.debug('ICUIExplorer', '[EXPL] modification event ignored for tree', { paths });
          break;
        }
        default: {
          log.debug('ICUIExplorer', '[EXPL] unknown filesystem_event', { event });
        }
      }
    };

    backendService.on('filesystem_event', handleFileSystemEvent);

    const topics = ['fs.file_created', 'fs.directory_created', 'fs.file_deleted', 'fs.file_moved', 'fs.file_copied', 'fs.file_modified'];

    const subscribeToEvents = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        if (!status.connected) return;
        log.info('ICUIExplorer', '[EXPL] Subscribing to fs topics');
        await backendService.notify('subscribe', { topics });
      } catch (error) {
        log.warn('ICUIExplorer', 'Failed to subscribe to filesystem events', { error });
      }
    };

    const initConnection = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        if (status.connected) {
          log.info('ICUIExplorer', '[EXPL] Initializing subscription on connected');
          await subscribeToEvents();
        } else {
          statusHandlerRef.current = async (payload: any) => {
            if (payload?.status === 'connected') {
              log.info('ICUIExplorer', '[EXPL] Connected, subscribing + refreshing');
              await subscribeToEvents();
              if (loadDirectoryRef.current) loadDirectoryRef.current(currentPath);
              if (statusHandlerRef.current) {
                backendService.off('connection_status_changed', statusHandlerRef.current);
                statusHandlerRef.current = null;
              }
            }
          };
          backendService.on('connection_status_changed', statusHandlerRef.current);
        }
      } catch (error) {
        console.error('[ICUIExplorer] Error initializing connection:', error);
      }
    };

    initConnection();

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
      backendService.off('filesystem_event', handleFileSystemEvent);
      if (statusHandlerRef.current) {
        backendService.off('connection_status_changed', statusHandlerRef.current);
        statusHandlerRef.current = null;
      }
      const cleanup = async () => {
        try {
          const status = await backendService.getConnectionStatus();
          if (status.connected) {
            log.info('ICUIExplorer', '[EXPL] Unsubscribing from fs topics');
            await backendService.notify('unsubscribe', { topics });
          }
        } catch (error) {
          log.warn('ICUIExplorer', 'Failed to unsubscribe from filesystem events', { error });
        }
      };
      cleanup();
    };
  }, [currentPath, onRefresh, loadDirectoryRef]);
}
