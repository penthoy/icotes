/**
 * Backend Connected Editor Component
 * Wraps ICUIEnhancedEditorPanel with ICPY backend integration
 * 
 * This component provides:
 * - Full backend file synchronization
 * - Real-time file content loading from backend filesystem
 * - Debounced auto-save to backend
 * - Code execution via backend services
 * - Error handling and connection status awareness
 * - Multi-file editing with backend state management
 */

import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import ICUIEnhancedEditorPanel, { ICUIEditorFile } from '../../../src/icui/components/panels/ICUIEnhancedEditorPanel';
import { useBackendState } from '../../../src/hooks/useBackendState';
import { useBackendContext } from '../../../src/contexts/BackendContext';

interface BackendConnectedEditorProps {
  className?: string;
  files?: ICUIEditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, newContent: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileReorder?: (fromIndex: number, toIndex: number) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
  enableDragDrop?: boolean;
  workspaceRoot?: string;
}

const BackendConnectedEditor: React.FC<BackendConnectedEditorProps> = ({
  className = '',
  files: propFiles,
  activeFileId: propActiveFileId,
  onFileChange: propOnFileChange,
  onFileClose: propOnFileClose,
  onFileCreate: propOnFileCreate,
  onFileSave: propOnFileSave,
  onFileRun: propOnFileRun,
  onFileActivate: propOnFileActivate,
  onFileReorder: propOnFileReorder,
  autoSave = true,
  autoSaveDelay = 1500,
  enableDragDrop = true,
  workspaceRoot
}) => {
  const { workspaceState, actions, error } = useBackendState();
  const { isConnected } = useBackendContext();
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Use backend state if no props provided, otherwise use props (for parent integration)
  const files = useMemo(() => {
    if (propFiles && propFiles.length > 0) {
      return propFiles;
    }
    
    return workspaceState?.files.map(file => ({
      id: file.id,
      name: file.name,
      language: file.language || getLanguageFromExtension(file.name),
      content: file.content || '',
      modified: file.modified || false,
    })) || [];
  }, [propFiles, workspaceState?.files]);

  const activeFileId = propActiveFileId || (files.length > 0 ? files[0].id : '');

  // Backend-integrated file operations
  const handleFileChange = useCallback(async (fileId: string, newContent: string) => {
    // Update local state immediately for responsive UI
    if (propOnFileChange) {
      propOnFileChange(fileId, newContent);
    }

    // Cancel previous auto-save timer
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    // Set up debounced auto-save if enabled and connected
    if (autoSave && isConnected) {
      autoSaveTimerRef.current = setTimeout(async () => {
        try {
          await actions.updateFile(fileId, newContent);
          console.log(`Auto-saved file ${fileId}`);
        } catch (error) {
          console.error(`Failed to auto-save file ${fileId}:`, error);
        }
      }, autoSaveDelay);
    }
  }, [actions, isConnected, autoSave, autoSaveDelay, propOnFileChange]);

  const handleFileClose = useCallback(async (fileId: string) => {
    try {
      if (propOnFileClose) {
        propOnFileClose(fileId);
      } else {
        await actions.closeFile(fileId);
      }
    } catch (error) {
      console.error(`Failed to close file ${fileId}:`, error);
    }
  }, [actions, propOnFileClose]);

  const handleFileCreate = useCallback(async () => {
    try {
      if (propOnFileCreate) {
        propOnFileCreate();
      } else {
        const fileName = `untitled-${Date.now()}.js`;
        const filePath = workspaceRoot ? `${workspaceRoot}/${fileName}` : fileName;
        const newFile = await actions.createFile(filePath, '// New file\nconsole.log("Hello, world!");');
        
        if (newFile) {
          await actions.openFile(newFile.id);
        }
      }
    } catch (error) {
      console.error('Failed to create file:', error);
    }
  }, [actions, workspaceRoot, propOnFileCreate]);

  const handleFileSave = useCallback(async (fileId: string) => {
    try {
      // Cancel auto-save timer since we're doing manual save
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
        autoSaveTimerRef.current = null;
      }

      if (propOnFileSave) {
        propOnFileSave(fileId);
      } else {
        // Get current content from the file
        const file = files.find(f => f.id === fileId);
        if (file) {
          await actions.saveFile(fileId, file.content);
        }
      }
      
      console.log(`Manually saved file ${fileId}`);
    } catch (error) {
      console.error(`Failed to save file ${fileId}:`, error);
    }
  }, [actions, propOnFileSave, files]);

  const handleFileRun = useCallback(async (fileId: string, content: string, language: string) => {
    try {
      if (propOnFileRun) {
        propOnFileRun(fileId, content, language);
      } else {
        const result = await actions.executeCode({ 
          fileId, 
          content, 
          language,
          workspaceRoot 
        });
        
        console.log('Code execution result:', result);
        
        // Show execution result notification
        if (result?.success) {
          showNotification('Code executed successfully', 'success');
        } else {
          showNotification(`Execution failed: ${result?.error || 'Unknown error'}`, 'error');
        }
      }
    } catch (error) {
      console.error('Failed to execute code:', error);
      showNotification(`Execution failed: ${error}`, 'error');
    }
  }, [actions, workspaceRoot, propOnFileRun]);

  const handleFileActivate = useCallback(async (fileId: string) => {
    try {
      if (propOnFileActivate) {
        propOnFileActivate(fileId);
      } else {
        await actions.setActiveFile(fileId);
        
        // Load file content if not already loaded
        const file = files.find(f => f.id === fileId);
        if (file && !file.content && isConnected) {
          try {
            const content = await actions.getFileContent(fileId);
            if (content !== undefined) {
              await actions.updateFile(fileId, content);
            }
          } catch (error) {
            console.error(`Failed to load content for file ${fileId}:`, error);
          }
        }
      }
    } catch (error) {
      console.error(`Failed to activate file ${fileId}:`, error);
    }
  }, [actions, files, isConnected, propOnFileActivate]);

  const handleFileReorder = useCallback(async (fromIndex: number, toIndex: number) => {
    try {
      if (propOnFileReorder) {
        propOnFileReorder(fromIndex, toIndex);
      } else {
        await actions.reorderFiles(fromIndex, toIndex);
      }
    } catch (error) {
      console.error('Failed to reorder files:', error);
    }
  }, [actions, propOnFileReorder]);

  // Clean up auto-save timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  // Load file content for active file if not loaded
  useEffect(() => {
    const loadActiveFileContent = async () => {
      const activeFile = files.find(f => f.id === activeFileId);
      if (activeFile && !activeFile.content && isConnected && !propFiles) {
        try {
          const content = await actions.getFileContent(activeFileId);
          if (content !== undefined) {
            await actions.updateFile(activeFileId, content);
          }
        } catch (error) {
          console.error(`Failed to load content for active file ${activeFileId}:`, error);
        }
      }
    };

    if (activeFileId) {
      loadActiveFileContent();
    }
  }, [activeFileId, files, isConnected, actions, propFiles]);

  // Show loading state if backend is loading and no files available
  if (isLoading && files.length === 0) {
    return (
      <div className={`backend-connected-editor loading ${className}`}>
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2"></div>
            <p className="text-sm text-gray-600">Loading files from backend...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show connection status if not connected
  if (!isConnected) {
    return (
      <div className={`backend-connected-editor disconnected ${className}`}>
        <div className="h-full">
          {/* Connection warning banner */}
          <div className="bg-yellow-100 border-l-4 border-yellow-500 p-3 mb-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">
                  Backend disconnected. File changes will not be saved.
                </p>
              </div>
            </div>
          </div>
          
          {/* Editor with limited functionality */}
          <ICUIEnhancedEditorPanel
            className="h-full"
            files={files}
            activeFileId={activeFileId}
            onFileChange={handleFileChange}
            onFileClose={handleFileClose}
            onFileCreate={handleFileCreate}
            onFileSave={handleFileSave}
            onFileRun={handleFileRun}
            onFileActivate={handleFileActivate}
            onFileReorder={handleFileReorder}
            autoSave={false} // Disable auto-save when disconnected
            autoSaveDelay={autoSaveDelay}
            enableDragDrop={enableDragDrop}
          />
        </div>
      </div>
    );
  }

  // Render fully connected editor
  return (
    <div className={`backend-connected-editor connected ${className}`}>
      {/* Connection status indicator */}
      <div className="flex items-center justify-between p-2 bg-green-50 border-b border-green-200">
        <div className="flex items-center text-sm text-green-700">
          <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
          Backend Connected
        </div>
        {workspaceRoot && (
          <div className="text-xs text-gray-500 truncate max-w-xs">
            Workspace: {workspaceRoot}
          </div>
        )}
      </div>

      {/* Main editor */}
      <ICUIEnhancedEditorPanel
        className="flex-1"
        files={files}
        activeFileId={activeFileId}
        onFileChange={handleFileChange}
        onFileClose={handleFileClose}
        onFileCreate={handleFileCreate}
        onFileSave={handleFileSave}
        onFileRun={handleFileRun}
        onFileActivate={handleFileActivate}
        onFileReorder={handleFileReorder}
        autoSave={autoSave}
        autoSaveDelay={autoSaveDelay}
        enableDragDrop={enableDragDrop}
      />
    </div>
  );
};

// Utility functions
function getLanguageFromExtension(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'js':
    case 'jsx':
      return 'javascript';
    case 'ts':
    case 'tsx':
      return 'typescript';
    case 'py':
      return 'python';
    case 'html':
      return 'html';
    case 'css':
      return 'css';
    case 'json':
      return 'json';
    case 'md':
    case 'markdown':
      return 'markdown';
    case 'yaml':
    case 'yml':
      return 'yaml';
    case 'xml':
      return 'xml';
    case 'sql':
      return 'sql';
    case 'sh':
    case 'bash':
      return 'shell';
    default:
      return 'text';
  }
}

function showNotification(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info'): void {
  const notification = document.createElement('div');
  const colors = {
    success: 'bg-green-500 text-white',
    error: 'bg-red-500 text-white',
    warning: 'bg-yellow-500 text-black',
    info: 'bg-blue-500 text-white'
  };
  
  notification.className = `fixed bottom-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${colors[type]}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

export default BackendConnectedEditor;
