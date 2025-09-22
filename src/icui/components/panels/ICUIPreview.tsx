/**
 * ICUI Preview Component
 * 
 * Provides live preview functionality for web applications using iframe-based rendering.
 * This implements Phase 1 of the Live Preview Plans with static file serving and
 * project type detection.
 * 
 * Features:
 * - Iframe-based preview for client-side applications
 * - Project type auto-detection (HTML, React, Vue, etc.)
 * - Real-time preview updates via WebSocket
 * - Built-in security via iframe sandbox
 * - Static file serving and build process integration
 */

import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { backendService, useTheme } from '../../services';
import { previewStateManager, type PreviewState, type PreviewProject } from '../../services/previewStateManager';

// Preview types and interfaces
interface PreviewFile {
  path: string;
  content: string;
}

interface ICUIPreviewRef {
  createPreview: (files: Record<string, string>) => Promise<void>;
  updatePreview: (files: Record<string, string>) => Promise<void>;
  clearPreview: () => void;
}

interface ICUIPreviewProps {
  className?: string;
  initialFiles?: Record<string, string>;
  onPreviewReady?: (url: string) => void;
  onPreviewError?: (error: string) => void;
  autoRefresh?: boolean;
  refreshDelay?: number;
}

const ICUIPreview = forwardRef<ICUIPreviewRef, ICUIPreviewProps>(({
  className = '',
  initialFiles = {},
  onPreviewReady,
  onPreviewError,
  autoRefresh = true,
  refreshDelay = 1000
}, ref) => {
  // Global state management for persistence across component unmount/remount
  const [globalState, setGlobalState] = useState<PreviewState>(() => previewStateManager.getState());
  const [isParentResizing, setIsParentResizing] = useState(false);
  
  // Subscribe to global state changes
  useEffect(() => {
    const unsubscribe = previewStateManager.subscribe(setGlobalState);
    return unsubscribe;
  }, []);

  // Extract state values for easy access
  const { currentProject, isLoading, error, previewUrl, connectionStatus } = globalState;
  
  // Update global state helper
  const updateGlobalState = useCallback((updates: Partial<PreviewState>) => {
    previewStateManager.updateState(updates);
  }, []);
  
  // Refs
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { theme } = useTheme();

  // Inject theme-aware scrollbar styles into the iframe document
  const injectScrollbarStyles = useCallback(() => {
    try {
      const iframe = iframeRef.current;
      if (!iframe) return;
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc) return;

      // Read colors from the parent theme CSS variables
      const root = document.documentElement;
      const computed = getComputedStyle(root);
      const track = (computed.getPropertyValue('--icui-bg-secondary') || '#1f2430').trim();
      const thumb = (computed.getPropertyValue('--icui-text-muted') || '#6e7681').trim();
      const border = (computed.getPropertyValue('--icui-border-subtle') || 'rgba(0,0,0,0.2)').trim();

      // Build CSS for WebKit and Firefox
      const css = `
        /* Firefox */
        html, body { scrollbar-width: thin; scrollbar-color: ${thumb} ${track}; }

        /* WebKit */
        *::-webkit-scrollbar { width: 10px; height: 10px; }
        *::-webkit-scrollbar-track { background: ${track}; }
        *::-webkit-scrollbar-thumb {
          background: ${thumb};
          border-radius: 8px;
          border: 2px solid ${track};
        }
        *::-webkit-scrollbar-thumb:hover {
          background: ${thumb};
          box-shadow: inset 0 0 0 1px ${border};
        }
      `;

      const STYLE_ID = 'icui-injected-scrollbar-style';
      let styleEl = doc.getElementById(STYLE_ID) as HTMLStyleElement | null;
      if (!styleEl) {
        styleEl = doc.createElement('style');
        styleEl.id = STYLE_ID;
        styleEl.setAttribute('data-origin', 'icui');
        doc.head?.appendChild(styleEl);
      }
      styleEl.textContent = css;
    } catch (e) {
      // Non-fatal; preview still works without custom scrollbars
      if (process.env.NODE_ENV === 'development') {
        console.warn('[ICUIPreview] Failed to inject scrollbar styles:', e);
      }
    }
  }, []);

  // Re-apply styles when theme changes
  useEffect(() => {
    injectScrollbarStyles();
  }, [theme, injectScrollbarStyles]);

  // Detect when parent is being resized by checking document cursor
  useEffect(() => {
    const checkResizeState = () => {
      const bodyStyle = window.getComputedStyle(document.body);
      const cursor = bodyStyle.cursor;
      const isResizing = cursor.includes('resize') || cursor === 'col-resize' || cursor === 'row-resize';
      
      // Only update state if it changed to avoid unnecessary re-renders during drag
      setIsParentResizing(current => current !== isResizing ? isResizing : current);
    };

    // Throttle the mutation observer to avoid excessive calls during drag
    let throttleTimer: NodeJS.Timeout | null = null;
    const throttledCheck = () => {
      if (throttleTimer) return;
      throttleTimer = setTimeout(() => {
        checkResizeState();
        throttleTimer = null;
      }, 16); // ~60fps throttling
    };

    // Create a MutationObserver to watch for cursor changes
    const observer = new MutationObserver(throttledCheck);
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['style']
    });

    // Also check on mount
    checkResizeState();

    return () => {
      observer.disconnect();
      if (throttleTimer) {
        clearTimeout(throttleTimer);
      }
    };
  }, []);

  // Notification service
  const showNotification = useCallback((message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    const notification = document.createElement('div');
    const colors = {
      success: 'bg-green-500 text-white',
      error: 'bg-red-500 text-white',
      warning: 'bg-yellow-500 text-black',
      info: 'bg-blue-500 text-white'
    };

    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${colors[type]}`;
    notification.textContent = message;
    notification.style.zIndex = '99999';
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }, []);

  // Safe clipboard function that handles different environments
  const copyToClipboard = useCallback(async (text: string): Promise<boolean> => {
    try {
      // Try modern Clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
      
      // Fallback to document.execCommand for older browsers/environments
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      const result = document.execCommand('copy');
      document.body.removeChild(textArea);
      
      if (result) {
        return true;
      }
      
      throw new Error('Copy command failed');
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      return false;
    }
  }, []);

  // Project type detection based on file patterns
  const detectProjectType = useCallback((files: Record<string, string>): string => {
    const fileNames = Object.keys(files);
    
    // Check for package.json to identify Node.js projects
    if (fileNames.includes('package.json')) {
      try {
        const packageJson = JSON.parse(files['package.json']);
        const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };
        
        if (dependencies.react || dependencies['@types/react']) {
          return 'react';
        }
        if (dependencies.vue || dependencies['@vue/cli']) {
          return 'vue';
        }
        if (dependencies.next || dependencies['next']) {
          return 'next';
        }
        if (dependencies.vite || dependencies['@vitejs/plugin-react']) {
          return 'vite';
        }
        return 'node';
      } catch (e) {
        console.warn('Failed to parse package.json:', e);
      }
    }
    
    // Check for static HTML files
    if (fileNames.some(name => name === 'index.html' || name.endsWith('.html'))) {
      return 'html';
    }
    
    // Check for JavaScript/TypeScript files
    if (fileNames.some(name => name.endsWith('.js') || name.endsWith('.mjs') || name.endsWith('.ts'))) {
      return 'javascript';
    }
    
    // Check for React/JSX files
    if (fileNames.some(name => name.endsWith('.jsx') || name.endsWith('.tsx'))) {
      return 'react';
    }
    
    // Check for Vue files
    if (fileNames.some(name => name.endsWith('.vue'))) {
      return 'vue';
    }
    
    // Check for CSS files
    if (fileNames.some(name => name.endsWith('.css') || name.endsWith('.scss') || name.endsWith('.sass'))) {
      return 'css';
    }
    
    // Check for Markdown files
    if (fileNames.some(name => name.endsWith('.md') || name.endsWith('.markdown'))) {
      return 'markdown';
    }
    
    // Check for Python Flask/Django
    if (fileNames.some(name => name === 'app.py' || name === 'main.py' || name === 'manage.py')) {
      return 'python-flask';
    }
    
    // Default to HTML for simple files
    return 'html';
  }, []);

  // Create a new preview
  const createPreview = useCallback(async (files: Record<string, string>) => {
    try {
      updateGlobalState({ isLoading: true, error: null });
      
      const projectType = detectProjectType(files);
      console.log('Detected project type:', projectType);
      
      // Send create preview request to backend
      const response = await fetch('/api/preview/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          files,
          projectType
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create preview: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      const project: PreviewProject = {
        id: result.preview_id,
        files,
        projectType,
        status: 'building',
        url: result.preview_url
      };
      
      updateGlobalState({ 
        currentProject: project, 
        previewUrl: result.preview_url 
      });
      
      // Poll for build completion
      await waitForPreviewReady(result.preview_id);
      
      // Re-read state after ready to ensure we have a URL
      const latest = previewStateManager.getState();
      const readyUrl = latest.previewUrl || project.url;
      if (readyUrl) {
        showNotification(`Preview created for ${projectType} project`, 'success');
        onPreviewReady?.(readyUrl);
      } else {
        console.warn('Preview reported ready but URL is missing');
      }
      
    } catch (error) {
      console.error('Failed to create preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      updateGlobalState({ error: errorMessage });
      showNotification(`Failed to create preview: ${errorMessage}`, 'error');
      onPreviewError?.(errorMessage);
    } finally {
      updateGlobalState({ isLoading: false });
    }
  }, [detectProjectType, onPreviewReady, onPreviewError, showNotification]);

  // Update existing preview
  const updatePreview = useCallback(async (files: Record<string, string>) => {
    if (!currentProject) {
      await createPreview(files);
      return;
    }
    
    try {
      updateGlobalState({ isLoading: true });
      
      // Send update request to backend
      const response = await fetch(`/api/preview/${currentProject.id}/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ files }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update preview: ${response.statusText}`);
      }
      
      updateGlobalState({ 
        currentProject: currentProject ? { ...currentProject, files, status: 'building' } : null 
      });
      
      // Wait for update to complete
      await waitForPreviewReady(currentProject.id);
      
      // Refresh iframe
      if (iframeRef.current) {
        iframeRef.current.src = iframeRef.current.src;
      }
      
      showNotification('Preview updated', 'success');
      
    } catch (error) {
      console.error('Failed to update preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      showNotification(`Failed to update preview: ${errorMessage}`, 'error');
    } finally {
      updateGlobalState({ isLoading: false });
    }
  }, [currentProject, createPreview, showNotification]);

  // Wait for preview to be ready
  const waitForPreviewReady = useCallback(async (previewId: string, maxAttempts: number = 10) => {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await fetch(`/api/preview/${previewId}/status`);
        if (response.ok) {
          const status = await response.json();
          if (status.ready) {
            // Read latest state to avoid stale closure issues
            const latest = previewStateManager.getState();
            const latestProject = latest.currentProject;
            if (latestProject && latestProject.id === previewId) {
              updateGlobalState({
                currentProject: { ...latestProject, status: 'ready' },
                // Prefer existing previewUrl; fall back to any url provided by status
                previewUrl: latest.previewUrl || status.preview_url || latestProject.url
              });
            }
            return;
          }
          if (status.error) {
            throw new Error(status.error);
          }
        }
      } catch (error) {
        console.warn(`Preview status check failed (attempt ${i + 1}):`, error);
      }
      
      // Wait before next attempt
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    throw new Error('Preview build timed out');
  }, []);

  // Clear current preview
  const clearPreview = useCallback(() => {
    if (currentProject) {
      // Send cleanup request to backend
      fetch(`/api/preview/${currentProject.id}`, { method: 'DELETE' })
        .catch(error => console.warn('Failed to cleanup preview:', error));
    }
    
    updateGlobalState({ 
      currentProject: null,
      previewUrl: '',
      error: null 
    });
    
    if (iframeRef.current) {
      iframeRef.current.src = 'about:blank';
    }
    
    showNotification('Preview cleared', 'info');
  }, [currentProject, showNotification]);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh && currentProject && Object.keys(initialFiles).length > 0) {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
      
      refreshTimerRef.current = setTimeout(() => {
        updatePreview(initialFiles);
      }, refreshDelay);
    }
    
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [initialFiles, autoRefresh, refreshDelay, currentProject, updatePreview]);

  // Check backend connection and validate persisted preview
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        updateGlobalState({ connectionStatus: status.connected });
        
        // If we have a persisted preview but backend is connected, validate it
        if (status.connected && currentProject?.id) {
          try {
            const response = await fetch(`/api/preview/${currentProject.id}/status`);
            if (!response.ok) {
              // Preview no longer exists on backend, clear it
              console.log('Persisted preview no longer exists on backend, clearing state');
              previewStateManager.clearState();
            }
          } catch (error) {
            // Preview validation failed, clear it
            console.log('Failed to validate persisted preview, clearing state');
            previewStateManager.clearState();
          }
        }
      } catch (error) {
        updateGlobalState({ connectionStatus: false });
      }
    };
    
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [currentProject?.id]);

  // Initialize with initial files
  useEffect(() => {
    // Only auto-create if we don't already have a persisted preview
    if (!currentProject && !previewUrl && Object.keys(initialFiles).length > 0 && connectionStatus) {
      createPreview(initialFiles);
    }
  }, [initialFiles, connectionStatus, createPreview, currentProject, previewUrl]);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    createPreview,
    updatePreview,
    clearPreview
  }), [createPreview, updatePreview, clearPreview]);

  // Cleanup on unmount - only for manual cleanup, not automatic
  useEffect(() => {
    return () => {
      // Don't auto-delete preview on unmount to allow external URL access
      // Users can manually clear using the clear button if needed
    };
  }, []);

  // When state is restored (after remount), ensure iframe displays the persisted URL
  useEffect(() => {
    // Only restore iframe if we have both a valid project and connection
    if (iframeRef.current && connectionStatus && currentProject?.status === 'ready' && (previewUrl || currentProject?.url)) {
      const target = previewUrl || currentProject?.url || '';
      if (iframeRef.current.src !== target && target) {
        try {
          // Avoid double reloads; set src only when different and valid
          iframeRef.current.src = target;
          console.log('Restored iframe src from persisted state:', target);
        } catch (e) {
          console.warn('Failed to set iframe src after remount:', e);
        }
      }
    }
  }, [previewUrl, currentProject?.url, currentProject?.status, connectionStatus]);

  return (
    <div className={`icui-preview-container h-full flex flex-col ${className}`}>
      {/* Preview Controls */}
      <div className="flex items-center justify-between p-2 border-b" style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)'
      }}>
        <div className="flex items-center space-x-2">
          {currentProject && (
            <span 
              className="text-xs px-2 py-1 rounded font-mono cursor-pointer hover:opacity-80 transition-opacity" 
              style={{
                backgroundColor: currentProject.status === 'ready' ? 'var(--icui-accent-success)' : 
                                currentProject.status === 'error' ? 'var(--icui-accent-error)' : 
                                'var(--icui-accent-warning)',
                color: 'white'
              }}
              onClick={async () => {
                const fullUrl = previewUrl ? `${window.location.origin}${previewUrl}` : 
                               currentProject.url ? `${window.location.origin}${currentProject.url}` : null;
                if (fullUrl) {
                  const success = await copyToClipboard(fullUrl);
                  if (success) {
                    showNotification('Preview URL copied to clipboard!', 'success');
                  } else {
                    showNotification('Failed to copy URL', 'error');
                  }
                }
              }}
              title="Click to copy full URL to clipboard"
            >
              {previewUrl ? `${window.location.origin}${previewUrl}` : 
               currentProject.url ? `${window.location.origin}${currentProject.url}` : 
               `${currentProject.projectType} - ${currentProject.status}`}
            </span>
          )}
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {currentProject && (
            <>
              <button
                onClick={() => {
                  if (iframeRef.current) {
                    iframeRef.current.src = iframeRef.current.src;
                  }
                }}
                className="px-2 py-1 text-xs rounded transition-colors"
                style={{
                  backgroundColor: 'var(--icui-bg-primary)',
                  borderColor: 'var(--icui-border-subtle)',
                  color: 'var(--icui-text-primary)'
                }}
                title="Refresh preview"
              >
                🔄
              </button>
              <button
                onClick={() => {
                  const fullUrl = previewUrl ? `${window.location.origin}${previewUrl}` : 
                                 currentProject.url ? `${window.location.origin}${currentProject.url}` : null;
                  if (fullUrl) {
                    window.open(fullUrl, '_blank');
                  }
                }}
                className="px-2 py-1 text-xs rounded transition-colors"
                style={{
                  backgroundColor: 'var(--icui-bg-primary)',
                  borderColor: 'var(--icui-border-subtle)',
                  color: 'var(--icui-text-primary)'
                }}
                title="Open preview in new tab"
              >
                🔗
              </button>
            </>
          )}
          <button
            onClick={clearPreview}
            disabled={!currentProject}
            className="px-2 py-1 text-xs rounded transition-colors disabled:opacity-50"
            style={{
              backgroundColor: 'var(--icui-bg-primary)',
              borderColor: 'var(--icui-border-subtle)',
              color: 'var(--icui-text-primary)'
            }}
            title="Clear preview"
          >
            🗑️
          </button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="flex-1 relative overflow-hidden">
        {/* Resize overlay - shown when parent is being resized */}
        {isParentResizing && (
          <div 
            className="absolute inset-0 z-10 bg-transparent"
            style={{ 
              cursor: 'inherit',
              pointerEvents: 'auto' 
            }}
          />
        )}
        
        {error ? (
          <div className="flex items-center justify-center h-full p-4">
            <div className="text-center">
              <div className="text-red-500 text-lg mb-2">⚠️</div>
              <p className="text-sm mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                Preview Error
              </p>
              <p className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                {error}
              </p>
              <button
                onClick={() => {
                  updateGlobalState({ error: null });
                  if (Object.keys(initialFiles).length > 0) {
                    createPreview(initialFiles);
                  }
                }}
                className="mt-3 px-3 py-1 text-xs rounded"
                style={{
                  backgroundColor: 'var(--icui-accent-primary)',
                  color: 'white'
                }}
              >
                Retry
              </button>
            </div>
          </div>
        ) : !connectionStatus ? (
          <div className="flex items-center justify-center h-full p-4">
            <div className="text-center">
              <div className="text-yellow-500 text-lg mb-2">⚠️</div>
              <p className="text-sm" style={{ color: 'var(--icui-text-primary)' }}>
                Backend Disconnected
              </p>
              <p className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                Please check your connection
              </p>
            </div>
          </div>
        ) : !currentProject ? (
          <div className="flex items-center justify-center h-full p-4">
            <div className="text-center">
              <div className="text-blue-500 text-lg mb-2">🖥️</div>
              <p className="text-sm mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                No Preview Available
              </p>
              <p className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                Create or open files to see a live preview
              </p>
            </div>
          </div>
        ) : (
          <iframe
            ref={iframeRef}
            src={previewUrl || currentProject?.url || ''}
            className="w-full h-full border-0"
            style={{
              pointerEvents: isParentResizing ? 'none' : 'auto'
            }}
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups allow-downloads allow-presentation"
            title="Live Preview"
            onLoad={() => {
              console.log('Preview iframe loaded');
              // Re-apply theme-aware scrollbar styles on every load/navigation
              injectScrollbarStyles();
            }}
            onError={() => {
              updateGlobalState({ error: 'Failed to load preview' });
            }}
          />
        )}
      </div>
    </div>
  );
});

ICUIPreview.displayName = 'ICUIPreview';

export default ICUIPreview;
export type { ICUIPreviewRef };