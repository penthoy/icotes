/**
 * ICUI Explorer Panel - Reference Implementation
 * A minimal, working file explorer panel for the ICUI framework
 * Following the same pattern as ICUITerminalPanel
 */

import React, { useRef, useEffect, useState } from 'react';

interface ICUIExplorerPanelProps {
  className?: string;
}

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  isExpanded?: boolean;
}

const ICUIExplorerPanel: React.FC<ICUIExplorerPanelProps> = ({ className = '' }) => {
  const [files, setFiles] = useState<FileNode[]>([
    {
      id: 'src',
      name: 'src',
      type: 'folder',
      path: '/src',
      isExpanded: true,
      children: [
        {
          id: 'components',
          name: 'components',
          type: 'folder',
          path: '/src/components',
          isExpanded: true,
          children: [
            { id: 'app-tsx', name: 'App.tsx', type: 'file', path: '/src/components/App.tsx' },
            { id: 'home-tsx', name: 'Home.tsx', type: 'file', path: '/src/components/Home.tsx' },
          ],
        },
        { id: 'main-tsx', name: 'main.tsx', type: 'file', path: '/src/main.tsx' },
      ],
    },
    {
      id: 'public',
      name: 'public',
      type: 'folder',
      path: '/public',
      isExpanded: false,
      children: [
        { id: 'index-html', name: 'index.html', type: 'file', path: '/public/index.html' },
      ],
    },
    { id: 'package-json', name: 'package.json', type: 'file', path: '/package.json' },
    { id: 'readme-md', name: 'README.md', type: 'file', path: '/README.md' },
  ]);

  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Toggle folder expansion
  const toggleFolder = (folderId: string) => {
    const updateNode = (nodes: FileNode[]): FileNode[] => {
      return nodes.map(node => {
        if (node.id === folderId && node.type === 'folder') {
          return { ...node, isExpanded: !node.isExpanded };
        }
        if (node.children) {
          return { ...node, children: updateNode(node.children) };
        }
        return node;
      });
    };
    setFiles(updateNode(files));
  };

  // Handle file/folder click
  const handleItemClick = (item: FileNode) => {
    if (item.type === 'folder') {
      toggleFolder(item.id);
    } else {
      setSelectedFile(item.id);
      console.log('File selected:', item.path);
    }
  };

  // Render file tree recursively
  const renderFileTree = (nodes: FileNode[], level: number = 0) => {
    return nodes.map(node => (
      <div key={node.id}>
        <div
          className={`flex items-center py-1 px-2 cursor-pointer hover:bg-gray-700 ${
            selectedFile === node.id ? 'bg-blue-600' : ''
          }`}
          style={{ paddingLeft: `${(level * 16) + 8}px` }}
          onClick={() => handleItemClick(node)}
        >
          <span className="mr-2 text-sm">
            {node.type === 'folder' ? (node.isExpanded ? '📂' : '📁') : '📄'}
          </span>
          <span className="text-sm text-white">{node.name}</span>
        </div>
        {node.type === 'folder' && node.isExpanded && node.children && (
          <div>
            {renderFileTree(node.children, level + 1)}
          </div>
        )}
      </div>
    ));
  };

  // Handle refresh action
  const handleRefresh = () => {
    console.log('Refreshing file explorer...');
    // In a real implementation, this would reload the file tree from the backend
  };

  return (
    <div className={`icui-explorer-panel h-full flex flex-col bg-black text-white ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700">
        <span className="text-sm font-medium">Explorer</span>
        <button
          onClick={handleRefresh}
          className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          Refresh
        </button>
      </div>

      {/* File tree */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-1">
          {renderFileTree(files)}
        </div>
      </div>

      {/* Status bar */}
      <div className="px-3 py-1 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
        {selectedFile ? `Selected: ${files.find(f => f.id === selectedFile)?.name || 'Unknown'}` : 'No file selected'}
      </div>
    </div>
  );
};

export default ICUIExplorerPanel;
