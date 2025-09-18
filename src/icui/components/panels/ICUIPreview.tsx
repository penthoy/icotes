/**
 * ICUI Preview Component
 * 
 * Provides live preview functionality for web applications using iframe-based rendering.
 * This implements Phase 1 of the Live Preview Plans with static file serving and
 * project type detection.
 * 
 * Key Features:
 * - Iframe-based preview for client-side applications
 * - Project type auto-detection (HTML, React, Vue, etc.)
 * - Real-time preview updates via WebSocket
 * - Built-in security via iframe sandbox
 * - Static file serving and build process integration
 */

import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { backendService, useTheme } from '../../services';

// Preview types and interfaces
interface PreviewFile {
  path: string;
  content: string;
}

interface PreviewProject {
  id: string;
  files: Record<string, string>;
  projectType: string;
  status: 'building' | 'ready' | 'error';
  url?: string;
  error?: string;
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
  // State management
  const [currentProject, setCurrentProject] = useState<PreviewProject | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [connectionStatus, setConnectionStatus] = useState<boolean>(false);
  
  // Refs
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
  const { theme } = useTheme();

  // Notification service
  const showNotification = useCallback((message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
    const notification = document.createElement('div');
    const colors = {
      success: 'bg-green-500 text-white',
      error: 'bg-red-500 text-white',
      warning: 'bg-yellow-500 text-black',
      info: 'bg-blue-500 text-white'
    };
    
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${colors[type]}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
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
      setIsLoading(true);
      setError(null);
      
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
      
      setCurrentProject(project);
      setPreviewUrl(result.preview_url);
      
      // Poll for build completion
      await waitForPreviewReady(result.preview_id);
      
      showNotification(`Preview created for ${projectType} project`, 'success');
      onPreviewReady?.(result.preview_url);
      
    } catch (error) {
      console.error('Failed to create preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(errorMessage);
      showNotification(`Failed to create preview: ${errorMessage}`, 'error');
      onPreviewError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [detectProjectType, onPreviewReady, onPreviewError, showNotification]);

  // Update existing preview
  const updatePreview = useCallback(async (files: Record<string, string>) => {
    if (!currentProject) {
      await createPreview(files);
      return;
    }
    
    try {
      setIsLoading(true);
      
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
      
      setCurrentProject(prev => prev ? { ...prev, files, status: 'building' } : null);
      
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
      setIsLoading(false);
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
            setCurrentProject(prev => prev ? { ...prev, status: 'ready' } : null);
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
    
    setCurrentProject(null);
    setPreviewUrl('');
    setError(null);
    
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

  // Check backend connection
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const status = await backendService.getConnectionStatus();
        setConnectionStatus(status.connected);
      } catch (error) {
        setConnectionStatus(false);
      }
    };
    
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Initialize with initial files
  useEffect(() => {
    if (Object.keys(initialFiles).length > 0 && connectionStatus) {
      createPreview(initialFiles);
    }
  }, [initialFiles, connectionStatus, createPreview]);

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    createPreview,
    updatePreview,
    clearPreview
  }), [createPreview, updatePreview, clearPreview]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (currentProject) {
        fetch(`/api/preview/${currentProject.id}`, { method: 'DELETE' })
          .catch(error => console.warn('Failed to cleanup preview on unmount:', error));
      }
    };
  }, [currentProject]);

  return (
    <div className={`icui-preview-container h-full flex flex-col ${className}`}>
      {/* Preview Controls */}
      <div className="flex items-center justify-between p-2 border-b" style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)'
      }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
            Live Preview
          </span>
          {currentProject && (
            <span className="text-xs px-2 py-1 rounded" style={{
              backgroundColor: currentProject.status === 'ready' ? 'var(--icui-accent-success)' : 
                              currentProject.status === 'error' ? 'var(--icui-accent-error)' : 
                              'var(--icui-accent-warning)',
              color: 'white'
            }}>
              {currentProject.projectType} - {currentProject.status}
            </span>
          )}
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {currentProject && (
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
                  setError(null);
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
            src={previewUrl}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
            title="Live Preview"
            onLoad={() => {
              console.log('Preview iframe loaded');
            }}
            onError={() => {
              setError('Failed to load preview');
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