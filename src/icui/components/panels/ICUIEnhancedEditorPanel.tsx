/**
 * ICUI Enhanced Editor Panel
 * Advanced code editor with tab support, syntax highlighting, and file management
 * Extracted and abstracted from ICUITest4 functionality
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import CodeEditor, { SupportedLanguage } from '../../../components/CodeEditor';

export interface ICUIEditorFile {
  id: string;
  name: string;
  content: string;
  language: SupportedLanguage;
  modified: boolean;
  path?: string;
}

export interface ICUIEnhancedEditorPanelProps {
  files?: ICUIEditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, content: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: SupportedLanguage) => void;
  onFileActivate?: (fileId: string) => void;
  className?: string;
  theme?: 'light' | 'dark';
  readOnly?: boolean;
  showLineNumbers?: boolean;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

// Default files for empty state
const defaultFiles: ICUIEditorFile[] = [
  {
    id: 'welcome',
    name: 'Welcome.js',
    content: `// Welcome to ICUI Enhanced Editor!
// This editor supports multiple files, syntax highlighting, and more

function welcomeMessage() {
  console.log("Welcome to the ICUI Framework!");
  return "Ready to code!";
}

// Try editing this file or create a new one using the + button
welcomeMessage();`,
    language: 'javascript',
    modified: false,
  }
];

// Language detection from filename
const getLanguageFromFileName = (fileName: string): SupportedLanguage => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'py': return 'python';
    case 'js': case 'jsx': case 'ts': case 'tsx': 
    case 'html': case 'htm': case 'css': case 'json': case 'md':
    default: return 'javascript';
  }
};

// File icon based on language
const getFileIcon = (language: SupportedLanguage): string => {
  switch (language) {
    case 'javascript': return '📄';
    case 'python': return '🐍';
    default: return '📄';
  }
};

export const ICUIEnhancedEditorPanel: React.FC<ICUIEnhancedEditorPanelProps> = ({
  files = defaultFiles,
  activeFileId,
  onFileChange,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  onFileActivate,
  className = '',
  theme = 'dark',
  readOnly = false,
  showLineNumbers = true,
  autoSave = false,
  autoSaveDelay = 2000,
}) => {
  const [internalFiles, setInternalFiles] = useState<ICUIEditorFile[]>(files);
  const [internalActiveId, setInternalActiveId] = useState<string>(activeFileId || files[0]?.id || '');
  const autoSaveTimeout = useRef<NodeJS.Timeout>();

  // Use controlled or uncontrolled mode
  const currentFiles = files;
  const currentActiveId = activeFileId || internalActiveId;
  const activeFile = currentFiles.find(f => f.id === currentActiveId);

  // Handle file content changes
  const handleContentChange = useCallback((fileId: string, content: string) => {
    if (!activeFile || readOnly) return;

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

    // Auto-save functionality
    if (autoSave) {
      if (autoSaveTimeout.current) {
        clearTimeout(autoSaveTimeout.current);
      }
      autoSaveTimeout.current = setTimeout(() => {
        onFileSave?.(fileId);
      }, autoSaveDelay);
    }
  }, [activeFile, readOnly, onFileChange, autoSave, autoSaveDelay, onFileSave]);

  // Handle tab switching
  const handleTabClick = useCallback((fileId: string) => {
    if (onFileActivate) {
      // Controlled mode - notify parent
      onFileActivate(fileId);
    } else {
      // Uncontrolled mode - update internal state
      setInternalActiveId(fileId);
    }
  }, [onFileActivate]);

  // Handle file close
  const handleFileClose = useCallback((fileId: string) => {
    if (onFileClose) {
      onFileClose(fileId);
    } else {
      setInternalFiles(prev => {
        const newFiles = prev.filter(f => f.id !== fileId);
        // Switch to another file if we closed the active one
        if (fileId === currentActiveId && newFiles.length > 0) {
          setInternalActiveId(newFiles[0].id);
        }
        return newFiles;
      });
    }
  }, [onFileClose, currentActiveId]);

  // Handle new file creation
  const handleNewFile = useCallback(() => {
    if (onFileCreate) {
      onFileCreate();
    } else {
      const newFile: ICUIEditorFile = {
        id: `file-${Date.now()}`,
        name: `untitled-${currentFiles.length + 1}.js`,
        content: '// New file\n',
        language: 'javascript',
        modified: true,
      };
      setInternalFiles(prev => [...prev, newFile]);
      setInternalActiveId(newFile.id);
    }
  }, [onFileCreate, currentFiles.length]);

  // Handle file save
  const handleFileSave = useCallback(() => {
    if (!activeFile) return;
    
    if (onFileSave) {
      onFileSave(activeFile.id);
    } else {
      setInternalFiles(prev => prev.map(f => 
        f.id === activeFile.id 
          ? { ...f, modified: false }
          : f
      ));
    }
  }, [activeFile, onFileSave]);

  // Handle code execution
  const handleRunCode = useCallback(() => {
    if (!activeFile) return;
    
    if (onFileRun) {
      onFileRun(activeFile.id, activeFile.content, activeFile.language);
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
  }, [activeFile, onFileRun]);

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
      if (autoSaveTimeout.current) {
        clearTimeout(autoSaveTimeout.current);
      }
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
              backgroundColor: file.id === currentActiveId ? 'var(--icui-bg-secondary)' : 'var(--icui-bg-tertiary)',
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
            {activeFile?.language.toUpperCase()}
          </span>
          {showLineNumbers && (
            <span className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
              Lines: {activeFile?.content.split('\n').length || 0}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleFileSave}
            disabled={!activeFile?.modified}
            className="text-xs px-2 py-1 rounded hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            style={{ backgroundColor: 'var(--icui-success)', color: 'var(--icui-text-primary)' }}
          >
            Save
          </button>
          <button
            onClick={handleRunCode}
            disabled={!activeFile}
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
                    theme={theme}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>{activeFile ? `${activeFile.language} • ${activeFile.name}` : 'No file selected'}</span>
        <span>Ctrl+S to save • Ctrl+N for new file • Ctrl+Enter to run</span>
      </div>
    </div>
  );
};

export default ICUIEnhancedEditorPanel;
