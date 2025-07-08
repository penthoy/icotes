/**
 * ICUI Editor Panel - Specialized panel for code editing functionality
 * Extends BasePanel with editor-specific features
 * Part of Phase 4: Specialized Panel Implementations
 */

import React, { useCallback, useState } from 'react';
import { ICUIBasePanel } from '../ICUIBasePanel';
import type { ICUIBasePanelProps } from '../../types/icui-panel';
import CodeEditor, { SupportedLanguage } from '../../../components/CodeEditor';
import FileTabs, { FileData } from '../../../components/FileTabs';
import { Save, FileText, Play } from 'lucide-react';

export interface ICUIEditorPanelProps extends Omit<ICUIBasePanelProps, 'children'> {
  /** Panel children are not needed as editor provides its own content */
  children?: React.ReactNode;
  /** Overall theme */
  theme?: 'light' | 'dark';
  /** Editor-specific options */
  editorOptions?: {
    /** Show file tabs */
    showTabs?: boolean;
    /** Enable code execution */
    enableExecution?: boolean;
    /** Auto-save interval in ms */
    autoSaveInterval?: number;
    /** Default language */
    defaultLanguage?: SupportedLanguage;
  };
  /** Files to display in the editor */
  files?: FileData[];
  /** Active file ID */
  activeFileId?: string;
  /** Callback when file content changes */
  onFileChange?: (fileId: string, content: string) => void;
  /** Callback when file is selected */
  onFileSelect?: (fileId: string) => void;
  /** Callback when file is closed */
  onFileClose?: (fileId: string) => void;
  /** Callback when new file is created */
  onNewFile?: () => void;
  /** Callback when code is executed */
  onRunCode?: (code: string, language: SupportedLanguage) => void;
}

/**
 * Editor Panel Component
 * Provides a dockable code editor interface with file tabs
 */
export const ICUIEditorPanel: React.FC<ICUIEditorPanelProps> = ({
  panel,
  theme = 'dark',
  editorOptions,
  files = [],
  activeFileId,
  onFileChange,
  onFileSelect,
  onFileClose,
  onNewFile,
  onRunCode,
  ...basePanelProps
}) => {
  const [localFiles, setLocalFiles] = useState<FileData[]>(files);
  const [localActiveFileId, setLocalActiveFileId] = useState<string>(activeFileId || files[0]?.id || '');

  // Use props if provided, otherwise use local state
  const currentFiles = files.length > 0 ? files : localFiles;
  const currentActiveFileId = activeFileId || localActiveFileId;
  const activeFile = currentFiles.find(f => f.id === currentActiveFileId);

  // Determine language based on file extension
  const getLanguageFromFileName = (fileName: string): SupportedLanguage => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'js':
      case 'jsx':
      case 'ts':
      case 'tsx':
        return 'javascript';
      case 'py':
        return 'python';
      default:
        return editorOptions?.defaultLanguage || 'javascript';
    }
  };

  // Handle code change
  const handleCodeChange = useCallback((newCode: string) => {
    if (!activeFile) return;

    if (onFileChange) {
      onFileChange(activeFile.id, newCode);
    } else {
      // Update local state if no external handler
      setLocalFiles(prev => 
        prev.map(file => 
          file.id === activeFile.id 
            ? { ...file, content: newCode, isModified: file.content !== newCode }
            : file
        )
      );
    }
  }, [activeFile, onFileChange]);

  // Handle file tab selection
  const handleFileSelect = useCallback((fileId: string) => {
    if (onFileSelect) {
      onFileSelect(fileId);
    } else {
      setLocalActiveFileId(fileId);
    }
  }, [onFileSelect]);

  // Handle file close
  const handleFileClose = useCallback((fileId: string) => {
    if (onFileClose) {
      onFileClose(fileId);
    } else {
      // Handle local file close
      const fileIndex = currentFiles.findIndex(f => f.id === fileId);
      if (fileIndex === -1) return;

      const newFiles = currentFiles.filter(f => f.id !== fileId);
      setLocalFiles(newFiles);

      // If we closed the active file, switch to an adjacent file
      if (currentActiveFileId === fileId) {
        const newActiveIndex = fileIndex > 0 ? fileIndex - 1 : 0;
        setLocalActiveFileId(newFiles[newActiveIndex]?.id || newFiles[0]?.id || '');
      }
    }
  }, [currentFiles, currentActiveFileId, onFileClose]);

  // Handle code execution
  const handleRunCode = useCallback(() => {
    if (!activeFile || !onRunCode) return;
    
    const language = getLanguageFromFileName(activeFile.name);
    onRunCode(activeFile.content, language);
  }, [activeFile, onRunCode, getLanguageFromFileName]);

  // Handle file save
  const handleSaveFile = useCallback(() => {
    if (!activeFile) return;
    
    // TODO: Implement actual file saving
    
    // Mark file as not modified
    if (!onFileChange) {
      setLocalFiles(prev => 
        prev.map(file => 
          file.id === activeFile.id 
            ? { ...file, isModified: false }
            : file
        )
      );
    }
  }, [activeFile, onFileChange]);

  return (
    <ICUIBasePanel
      {...basePanelProps}
      panel={panel}
      headerProps={{
        ...basePanelProps.headerProps,
        // Could add editor-specific header actions here
      }}
    >
      <div className="flex flex-col h-full">
        {/* File Tabs */}
        {editorOptions?.showTabs !== false && currentFiles.length > 0 && (
          <FileTabs
            files={currentFiles}
            activeFileId={currentActiveFileId}
            onFileSelect={handleFileSelect}
            onFileClose={handleFileClose}
            onNewFile={onNewFile}
          />
        )}
        
        {/* Editor */}
        <div className="flex-1 relative">
          {activeFile ? (
            <CodeEditor
              code={activeFile.content}
              language={getLanguageFromFileName(activeFile.name)}
              onCodeChange={handleCodeChange}
              theme={theme}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>No file selected</p>
                {onNewFile && (
                  <button
                    onClick={onNewFile}
                    className="mt-2 px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
                  >
                    Create New File
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Editor Actions Bar (if file is active) */}
        {activeFile && (
          <div className="flex items-center justify-between p-2 border-t border-border bg-muted/30">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {getLanguageFromFileName(activeFile.name).toUpperCase()}
              </span>
              {activeFile.isModified && (
                <span className="text-xs text-orange-500">Modified</span>
              )}
            </div>
            
            <div className="flex items-center gap-1">
              <button
                onClick={handleSaveFile}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title="Save File"
              >
                <Save className="h-4 w-4" />
              </button>
              
              {editorOptions?.enableExecution && onRunCode && (
                <button
                  onClick={handleRunCode}
                  className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                  title="Run Code"
                >
                  <Play className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </ICUIBasePanel>
  );
};

export default ICUIEditorPanel;
