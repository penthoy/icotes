/**
 * ICUI Enhanced Editor Panel
 * Advanced code editor with tab support, syntax highlighting, and file management
 * Extracted and abstracted from ICUITest4 functionality
 */

import React, { useState, useEffect, useCallback } from 'react';
import CodeEditor, { SupportedLanguage } from '../../../components/CodeEditor';

export interface ICUIEditorFile {
  id: string;
  name: string;
  content: string;
  language: SupportedLanguage;
  modified?: boolean;
}

// Keep internal FileData for backward compatibility
interface FileData {
  id: string;
  name: string;
  content: string;
  language: SupportedLanguage;
  modified?: boolean;
}

export interface ICUIEnhancedEditorPanelProps {
  className?: string;
  files?: FileData[];
  activeFileId?: string;
  onFileChange?: (fileId: string, content: string) => void;
  onFileAdd?: (file: FileData) => void;
  onFileRemove?: (fileId: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

export const ICUIEnhancedEditorPanel: React.FC<ICUIEnhancedEditorPanelProps> = ({
  className = '',
  files: externalFiles,
  activeFileId: externalActiveFileId,
  onFileChange,
  onFileAdd,
  onFileRemove,
  onFileActivate,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  autoSave = false,
  autoSaveDelay = 1500,
}) => {
  // Internal state for standalone usage
  const [internalFiles, setInternalFiles] = useState<FileData[]>([
    {
      id: 'default-js',
      name: 'main.js',
      content: `// Enhanced ICUI Editor with Tabs!
// Much cleaner implementation using the Framework

function enhancedExample() {
  console.log("Framework does the heavy lifting!");
  return "less code, more functionality";
}

enhancedExample();`,
      language: 'javascript',
      modified: false,
    },
  ]);
  const [internalActiveFileId, setInternalActiveFileId] = useState('default-js');
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  // Detect theme on mount and when it changes
  useEffect(() => {
    const detectTheme = () => {
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains('dark') || 
                     htmlElement.classList.contains('icui-theme-github-dark') ||
                     htmlElement.classList.contains('icui-theme-monokai') ||
                     htmlElement.classList.contains('icui-theme-one-dark');
      setIsDarkTheme(isDark);
    };

    detectTheme();
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Use external or internal state
  const currentFiles = externalFiles || internalFiles;
  const currentActiveId = externalActiveFileId || internalActiveFileId;

  // Get background colors based on theme - FIXED: Active tabs should be lighter
  const getTabBackgroundColor = (isActive: boolean) => {
    if (isDarkTheme) {
      // Dark themes: active tabs are LIGHTER, inactive tabs are DARKER
      return isActive ? 'var(--icui-bg-secondary)' : 'var(--icui-bg-tertiary)';
    } else {
      // Light themes: active tabs are lighter, inactive tabs are darker  
      return isActive ? 'var(--icui-bg-secondary)' : 'var(--icui-bg-tertiary)';
    }
  };

  // Handle file content changes
  const handleContentChange = useCallback((fileId: string, content: string) => {
    const activeFile = currentFiles.find(f => f.id === fileId);
    if (!activeFile) return;

    if (onFileChange) {
      // Controlled mode
      onFileChange(fileId, content);
    } else {
      // Uncontrolled mode
      setInternalFiles(prev => prev.map(f => 
        f.id === fileId 
          ? { ...f, content, modified: true }
          : f
      ));
    }
  }, [currentFiles, onFileChange]);

  // Handle tab switching
  const handleTabClick = useCallback((fileId: string) => {
    if (onFileActivate) {
      // Controlled mode - notify parent
      onFileActivate(fileId);
    } else {
      // Uncontrolled mode - update internal state
      setInternalActiveFileId(fileId);
    }
  }, [onFileActivate]);

  // Handle file close - Updated to use onFileClose prop
  const handleFileClose = useCallback((fileId: string) => {
    if (onFileClose) {
      onFileClose(fileId);
    } else if (onFileRemove) {
      onFileRemove(fileId);
    } else {
      setInternalFiles(prev => {
        const newFiles = prev.filter(f => f.id !== fileId);
        // Switch to another file if we closed the active one
        if (fileId === currentActiveId && newFiles.length > 0) {
          setInternalActiveFileId(newFiles[0].id);
        }
        return newFiles;
      });
    }
  }, [onFileClose, onFileRemove, currentActiveId]);

  // Handle new file creation
  const handleNewFile = useCallback(() => {
    if (onFileCreate) {
      onFileCreate();
    } else if (onFileAdd) {
      onFileAdd({
        id: `file-${Date.now()}`,
        name: `untitled-${currentFiles.length + 1}.js`,
        content: '// New file\n',
        language: 'javascript',
        modified: true,
      });
    } else {
      const newFile: FileData = {
        id: `file-${Date.now()}`,
        name: `untitled-${currentFiles.length + 1}.js`,
        content: '// New file\n',
        language: 'javascript',
        modified: true,
      };
      setInternalFiles(prev => [...prev, newFile]);
      setInternalActiveFileId(newFile.id);
    }
  }, [onFileCreate, onFileAdd, currentFiles.length]);

  // Handle file save
  const handleFileSave = useCallback(() => {
    const activeFile = currentFiles.find(f => f.id === currentActiveId);
    if (!activeFile) return;
    
    if (onFileSave) {
      onFileSave(activeFile.id);
    } else if (onFileChange) {
      onFileChange(activeFile.id, activeFile.content);
    } else {
      setInternalFiles(prev => prev.map(f => 
        f.id === activeFile.id 
          ? { ...f, modified: false }
          : f
      ));
    }
  }, [currentFiles, currentActiveId, onFileSave, onFileChange]);

  // Handle code execution
  const handleRunCode = useCallback(() => {
    const activeFile = currentFiles.find(f => f.id === currentActiveId);
    if (!activeFile) return;
    
    if (onFileRun) {
      onFileRun(activeFile.id, activeFile.content, activeFile.language);
    } else if (onFileChange) {
      onFileChange(activeFile.id, activeFile.content);
    } else {
      // Default execution for JavaScript
      if (activeFile.language === 'javascript') {
        try {
          const result = eval(activeFile.content);
          console.log('Code execution result:', result);
        } catch (error) {
          console.error('Code execution error:', error);
        }
      }
    }
  }, [currentFiles, currentActiveId, onFileRun, onFileChange]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 's':
          e.preventDefault();
          handleFileSave();
          break;
        case 'n':
          e.preventDefault();
          handleNewFile();
          break;
        case 'Enter':
          e.preventDefault();
          handleRunCode();
          break;
      }
    }
  }, [handleFileSave, handleNewFile, handleRunCode]);

  // Register keyboard shortcuts
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Cleanup auto-save timeout
  useEffect(() => {
    return () => {
      // No auto-save timeout to clear as it's not implemented in the new structure
    };
  }, []);

  if (currentFiles.length === 0) {
    return (
      <div className={`icui-enhanced-editor-panel h-full flex flex-col bg-gray-900 ${className}`}>
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-2xl mb-2">📝</div>
            <div className="mb-4">No files open</div>
            <button
              onClick={handleNewFile}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Create New File
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`icui-enhanced-editor-panel h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Tab Bar */}
      <div className="flex items-center overflow-x-auto border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        {currentFiles.map(file => (
          <div
            key={file.id}
            className={`
              flex items-center px-3 py-2 text-sm cursor-pointer border-r
              min-w-[140px] max-w-[200px] select-none hover:opacity-80 transition-opacity
            `}
            style={{
              backgroundColor: getTabBackgroundColor(file.id === currentActiveId),
              borderRightColor: 'var(--icui-border-subtle)',
              color: file.id === currentActiveId ? 'var(--icui-text-primary)' : 'var(--icui-text-secondary)'
            }}
            onClick={() => handleTabClick(file.id)}
          >
            <span className="mr-2">{getFileIcon(file.language)}</span>
            <span className="flex-1 truncate">{file.name}</span>
            {file.modified && <span className="ml-1 text-xs" style={{ color: 'var(--icui-warning)' }}>●</span>}
            {currentFiles.length > 1 && (
              <button
                className="ml-2 text-xs w-4 h-4 flex items-center justify-center hover:opacity-80 transition-opacity"
                style={{ color: 'var(--icui-text-secondary)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleFileClose(file.id);
                }}
                title="Close file"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <button
          onClick={handleNewFile}
          className="px-3 py-2 text-sm border-r hover:opacity-80 transition-opacity"
          style={{ backgroundColor: 'var(--icui-accent)', borderRightColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-primary)' }}
          title="New file"
        >
          +
        </button>
      </div>

      {/* Editor Controls */}
      <div className="flex items-center justify-between px-3 py-1 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
            {currentFiles.find(f => f.id === currentActiveId)?.language.toUpperCase()}
          </span>
          {/* showLineNumbers is not directly controlled by this component's props,
              so it's removed from the status bar as per the new_code. */}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleFileSave}
            disabled={!currentFiles.find(f => f.id === currentActiveId)?.modified}
            className="text-xs px-2 py-1 rounded hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            style={{ backgroundColor: 'var(--icui-success)', color: 'var(--icui-text-primary)' }}
          >
            Save
          </button>
          <button
            onClick={handleRunCode}
            disabled={!currentFiles.find(f => f.id === currentActiveId)}
            className="text-xs px-2 py-1 rounded hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor Content Area */}
      <div className="flex-1 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        {currentFiles.length === 0 ? (
          <div className="h-full flex items-center justify-center" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-muted)' }}>
            <div className="text-center">
              <div className="text-4xl mb-4">📝</div>
              <div className="text-lg font-medium mb-2">No files open</div>
              <div className="text-sm">Create a new file or open an existing one to start editing</div>
            </div>
          </div>
        ) : (
          <div className="h-full" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
            {currentFiles.map(file => (
              <div
                key={file.id}
                className={`h-full ${file.id === currentActiveId ? 'block' : 'hidden'}`}
                style={{ backgroundColor: 'var(--icui-bg-primary)' }}
              >
                {/* Use CodeEditor component for syntax highlighting */}
                <div style={{ height: '100%', backgroundColor: 'var(--icui-bg-primary)' }}>
                  <CodeEditor
                    code={file.content}
                    language={file.language}
                    onCodeChange={(content: string) => handleContentChange(file.id, content)}
                    theme={isDarkTheme ? 'dark' : 'light'} // Pass theme to CodeEditor
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>{currentFiles.find(f => f.id === currentActiveId) ? `${currentFiles.find(f => f.id === currentActiveId)?.language} • ${currentFiles.find(f => f.id === currentActiveId)?.name}` : 'No file selected'}</span>
        <span>Ctrl+S to save • Ctrl+N for new file • Ctrl+Enter to run</span>
      </div>
    </div>
  );
};

// File icon based on language
const getFileIcon = (language: SupportedLanguage): string => {
  switch (language) {
    case 'javascript': return '📄';
    case 'python': return '🐍';
    default: return '📄';
  }
};

export default ICUIEnhancedEditorPanel;
