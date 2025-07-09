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
  const handleContentChange = useCallback((content: string) => {
    if (!activeFile || readOnly) return;

    if (onFileChange) {
      // Controlled mode
      onFileChange(activeFile.id, content);
    } else {
      // Uncontrolled mode
      setInternalFiles(prev => prev.map(f => 
        f.id === activeFile.id 
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
        onFileSave?.(activeFile.id);
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
    <div className={`icui-enhanced-editor-panel h-full flex flex-col bg-gray-900 ${className}`}>
      {/* Tab Bar */}
      <div className="flex items-center bg-gray-800 border-b border-gray-700 overflow-x-auto">
        {currentFiles.map(file => (
          <div
            key={file.id}
            className={`
              flex items-center px-3 py-2 text-sm cursor-pointer border-r border-gray-700
              min-w-[140px] max-w-[200px] select-none
              ${file.id === currentActiveId 
                ? 'bg-gray-900 text-white' 
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }
            `}
            onClick={() => handleTabClick(file.id)}
          >
            <span className="mr-2">{getFileIcon(file.language)}</span>
            <span className="flex-1 truncate">{file.name}</span>
            {file.modified && <span className="ml-1 text-orange-500 text-xs">●</span>}
            {currentFiles.length > 1 && (
              <button
                className="ml-2 text-gray-400 hover:text-red-500 text-xs w-4 h-4 flex items-center justify-center"
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
          className="px-3 py-2 text-sm bg-blue-500 text-white hover:bg-blue-600 border-r border-gray-700"
          title="New file"
        >
          +
        </button>
      </div>

      {/* Editor Controls */}
      <div className="flex items-center justify-between px-3 py-1 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-400">
            {activeFile?.language.toUpperCase()}
          </span>
          {showLineNumbers && (
            <span className="text-xs text-gray-400">
              Lines: {activeFile?.content.split('\n').length || 0}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleFileSave}
            disabled={!activeFile?.modified}
            className="text-xs px-2 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-white"
          >
            Save
          </button>
          <button
            onClick={handleRunCode}
            disabled={!activeFile}
            className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-white"
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeFile && (
          <CodeEditor
            code={activeFile.content}
            language={activeFile.language}
            onCodeChange={handleContentChange}
            theme={theme}
          />
        )}
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 bg-gray-800 border-t border-gray-700 text-xs text-gray-400 flex justify-between">
        <span>
          {activeFile ? `${activeFile.name} - ${activeFile.language}` : 'No file selected'}
        </span>
        <span>
          Ctrl+S: Save • Ctrl+N: New File • Ctrl+Enter: Run
          {autoSave && ' • Auto-save enabled'}
        </span>
      </div>
    </div>
  );
};

export default ICUIEnhancedEditorPanel;
