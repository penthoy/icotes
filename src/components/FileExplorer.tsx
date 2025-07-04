import React, { useState } from "react";
import { 
  ChevronDown, 
  ChevronRight, 
  FileText, 
  FolderOpen, 
  Folder, 
  Plus, 
  MoreVertical 
} from "lucide-react";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  isExpanded?: boolean;
}

interface FileExplorerProps {
  files: FileNode[];
  onFileSelect: (filePath: string) => void;
  onFileCreate: (folderPath: string) => void;
  onFolderCreate: (folderPath: string) => void;
  onFileDelete: (filePath: string) => void;
  onFileRename: (oldPath: string, newName: string) => void;
  className?: string;
}

const FileExplorer: React.FC<FileExplorerProps> = ({
  files,
  onFileSelect,
  onFileCreate,
  onFolderCreate,
  onFileDelete,
  onFileRename,
  className = "",
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'js':
      case 'jsx':
      case 'ts':
      case 'tsx':
        return '📄';
      case 'json':
        return '📋';
      case 'md':
        return '📝';
      case 'css':
        return '🎨';
      case 'html':
        return '🌐';
      default:
        return '📄';
    }
  };

  const renderFileNode = (node: FileNode, level: number = 0) => {
    const isExpanded = expandedFolders.has(node.id);
    const paddingLeft = level * 16;

    return (
      <div key={node.id} className="select-none">
        <div 
          className={`flex items-center hover:bg-accent/50 cursor-pointer py-1 px-2 rounded-sm group`}
          style={{ paddingLeft: `${paddingLeft + 8}px` }}
        >
          {node.type === 'folder' ? (
            <div 
              className="flex items-center flex-1 min-w-0"
              onClick={() => toggleFolder(node.id)}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 mr-1 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-1 text-muted-foreground" />
              )}
              {isExpanded ? (
                <FolderOpen className="h-4 w-4 mr-2 text-blue-500" />
              ) : (
                <Folder className="h-4 w-4 mr-2 text-blue-500" />
              )}
              <span className="text-sm truncate">{node.name}</span>
            </div>
          ) : (
            <div 
              className="flex items-center flex-1 min-w-0"
              onClick={() => onFileSelect(node.path)}
            >
              <span className="mr-2 text-sm">{getFileIcon(node.name)}</span>
              <span className="text-sm truncate">{node.name}</span>
            </div>
          )}
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {node.type === 'folder' && (
                <>
                  <DropdownMenuItem onClick={() => onFileCreate(node.path)}>
                    <FileText className="h-4 w-4 mr-2" />
                    New File
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onFolderCreate(node.path)}>
                    <Folder className="h-4 w-4 mr-2" />
                    New Folder
                  </DropdownMenuItem>
                </>
              )}
              <DropdownMenuItem onClick={() => onFileRename(node.path, node.name)}>
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem 
                onClick={() => onFileDelete(node.path)}
                className="text-destructive"
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderFileNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`flex flex-col h-full bg-background border-r border-border ${className}`}>
      <div className="flex items-center justify-between p-2 border-b border-border">
        <h3 className="text-sm font-medium text-foreground">EXPLORER</h3>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => onFileCreate('/')}
            title="New File"
          >
            <FileText className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => onFolderCreate('/')}
            title="New Folder"
          >
            <Folder className="h-3 w-3" />
          </Button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto p-1">
        {files.map(file => renderFileNode(file))}
      </div>
    </div>
  );
};

export default FileExplorer;
