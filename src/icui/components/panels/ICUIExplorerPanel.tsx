/**
 * ICUI Explorer Panel - Specialized panel for file exploration functionality
 * Extends BasePanel with explorer-specific features
 * Part of Phase 4: Specialized Panel Implementations
 */

import React, { useCallback, useState } from 'react';
import { ICUIBasePanel } from '../ICUIBasePanel';
import type { ICUIBasePanelProps } from '../../types/icui-panel';
import FileExplorer from '../../../components/FileExplorer';
import { FolderPlus, FilePlus, RefreshCw } from 'lucide-react';

// File explorer data structure (matching existing implementation)
interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  isExpanded?: boolean;
}

export interface ICUIExplorerPanelProps extends Omit<ICUIBasePanelProps, 'children'> {
  /** Panel children are not needed as explorer provides its own content */
  children?: React.ReactNode;
  /** Overall theme */
  theme?: 'light' | 'dark';
  /** Explorer-specific options */
  explorerOptions?: {
    /** Show hidden files */
    showHidden?: boolean;
    /** Enable file operations */
    enableOperations?: boolean;
    /** Root path to explore */
    rootPath?: string;
    /** Auto-refresh interval in ms */
    autoRefresh?: number;
  };
  /** Files/folders to display */
  files?: FileNode[];
  /** Callback when file is selected */
  onFileSelect?: (filePath: string) => void;
  /** Callback when file is created */
  onFileCreate?: (folderPath: string) => void;
  /** Callback when folder is created */
  onFolderCreate?: (folderPath: string) => void;
  /** Callback when file is deleted */
  onFileDelete?: (filePath: string) => void;
  /** Callback when file is renamed */
  onFileRename?: (oldPath: string, newName: string) => void;
  /** Callback when explorer needs to refresh */
  onRefresh?: () => void;
}

/**
 * Explorer Panel Component
 * Provides a dockable file explorer interface
 */
export const ICUIExplorerPanel: React.FC<ICUIExplorerPanelProps> = ({
  panel,
  theme = 'dark',
  explorerOptions,
  files = [],
  onFileSelect,
  onFileCreate,
  onFolderCreate,
  onFileDelete,
  onFileRename,
  onRefresh,
  ...basePanelProps
}) => {
  const [localFiles, setLocalFiles] = useState<FileNode[]>(files);
  
  // Use props if provided, otherwise use local state
  const currentFiles = files.length > 0 ? files : localFiles;

  // Handle file selection
  const handleFileSelect = useCallback((filePath: string) => {
    if (onFileSelect) {
      onFileSelect(filePath);
    }
  }, [onFileSelect]);

  // Handle file creation
  const handleFileCreate = useCallback((folderPath: string) => {
    if (onFileCreate) {
      onFileCreate(folderPath);
    } else {
      // Create a new file in local state
      const newFile: FileNode = {
        id: `file-${Date.now()}`,
        name: 'new-file.txt',
        type: 'file',
        path: `${folderPath}/new-file.txt`,
      };
      
      setLocalFiles(prev => [...prev, newFile]);
    }
  }, [onFileCreate]);

  // Handle folder creation
  const handleFolderCreate = useCallback((folderPath: string) => {
    if (onFolderCreate) {
      onFolderCreate(folderPath);
    } else {
      // Create a new folder in local state
      const newFolder: FileNode = {
        id: `folder-${Date.now()}`,
        name: 'new-folder',
        type: 'folder',
        path: `${folderPath}/new-folder`,
        children: [],
        isExpanded: false,
      };
      
      setLocalFiles(prev => [...prev, newFolder]);
    }
  }, [onFolderCreate]);

  // Handle file deletion
  const handleFileDelete = useCallback((filePath: string) => {
    if (onFileDelete) {
      onFileDelete(filePath);
    } else {
      // Remove file from local state
      setLocalFiles(prev => prev.filter(file => file.path !== filePath));
    }
  }, [onFileDelete]);

  // Handle file renaming
  const handleFileRename = useCallback((oldPath: string, newName: string) => {
    if (onFileRename) {
      onFileRename(oldPath, newName);
    } else {
      // Rename file in local state
      setLocalFiles(prev => 
        prev.map(file => 
          file.path === oldPath 
            ? { ...file, name: newName, path: oldPath.replace(file.name, newName) }
            : file
        )
      );
    }
  }, [onFileRename]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    if (onRefresh) {
      onRefresh();
    } else {
      // Could implement local refresh logic here
    }
  }, [onRefresh]);

  // Handle create new file at root
  const handleCreateNewFile = useCallback(() => {
    const rootPath = explorerOptions?.rootPath || '/';
    handleFileCreate(rootPath);
  }, [explorerOptions?.rootPath, handleFileCreate]);

  // Handle create new folder at root
  const handleCreateNewFolder = useCallback(() => {
    const rootPath = explorerOptions?.rootPath || '/';
    handleFolderCreate(rootPath);
  }, [explorerOptions?.rootPath, handleFolderCreate]);

  return (
    <ICUIBasePanel
      {...basePanelProps}
      panel={panel}
      headerProps={{
        ...basePanelProps.headerProps,
        // Could add explorer-specific header actions here
      }}
    >
      <div className="flex flex-col h-full">
        {/* Explorer Toolbar */}
        {explorerOptions?.enableOperations !== false && (
          <div className="flex items-center justify-between p-2 border-b border-border bg-muted/30">
            <span className="text-sm font-medium text-muted-foreground">
              {explorerOptions?.rootPath ? explorerOptions.rootPath : 'Files'}
            </span>
            
            <div className="flex items-center gap-1">
              <button
                onClick={handleCreateNewFile}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title="New File"
              >
                <FilePlus className="h-4 w-4" />
              </button>
              
              <button
                onClick={handleCreateNewFolder}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title="New Folder"
              >
                <FolderPlus className="h-4 w-4" />
              </button>
              
              <button
                onClick={handleRefresh}
                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                title="Refresh"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
        
        {/* File Explorer */}
        <div className="flex-1 overflow-auto">
          {currentFiles.length > 0 ? (
            <FileExplorer
              files={currentFiles}
              onFileSelect={handleFileSelect}
              onFileCreate={handleFileCreate}
              onFolderCreate={handleFolderCreate}
              onFileDelete={handleFileDelete}
              onFileRename={handleFileRename}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <FolderPlus className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p className="mb-2">No files or folders</p>
                {explorerOptions?.enableOperations !== false && (
                  <div className="space-y-1">
                    <button
                      onClick={handleCreateNewFile}
                      className="block mx-auto px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
                    >
                      Create File
                    </button>
                    <button
                      onClick={handleCreateNewFolder}
                      className="block mx-auto px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded hover:bg-secondary/90"
                    >
                      Create Folder
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Explorer Status */}
        <div className="p-2 border-t border-border bg-muted/30">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {currentFiles.filter(f => f.type === 'file').length} files, {' '}
              {currentFiles.filter(f => f.type === 'folder').length} folders
            </span>
            
            {explorerOptions?.showHidden && (
              <span>Hidden files shown</span>
            )}
          </div>
        </div>
      </div>
    </ICUIBasePanel>
  );
};

export default ICUIExplorerPanel;
