/**
 * ICUI Test 8.1 - Explorer Multi-Select & Context Menus
 * 
 * Test page for Phase 8.1 implementation:
 * - Multi-select with Shift/Ctrl support
 * - Right-click context menus with file operations
 * - Keyboard navigation
 * - Batch operations
 */

import React, { useState } from 'react';
import ICUIEnhancedExplorer from '../../../src/icui/components/panels/ICUIEnhancedExplorer';
import { ICUIFileNode } from '../../../src/icui/services';

const ICUITest81: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<ICUIFileNode | null>(null);
  const [messages, setMessages] = useState<string[]>([]);

  const addMessage = (message: string) => {
    setMessages(prev => [...prev.slice(-10), `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const handleFileSelect = (file: ICUIFileNode) => {
    setSelectedFile(file);
    addMessage(`Selected: ${file.name} (${file.type})`);
  };

  const handleFileDoubleClick = (file: ICUIFileNode) => {
    addMessage(`Double-clicked: ${file.name} - Opening file...`);
    // In a real implementation, this would open the file in an editor
  };

  const handleFileCreate = (path: string) => {
    addMessage(`Created file: ${path}`);
  };

  const handleFolderCreate = (path: string) => {
    addMessage(`Created folder: ${path}`);
  };

  const handleFileDelete = (path: string) => {
    addMessage(`Deleted: ${path}`);
  };

  const handleFileRename = (oldPath: string, newPath: string) => {
    addMessage(`Renamed: ${oldPath} → ${newPath}`);
  };

  return (
    <div style={{
      height: '100vh',
      backgroundColor: 'var(--icui-bg-primary)',
      color: 'var(--icui-text-primary)',
      fontFamily: 'var(--icui-font-mono)'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid var(--icui-border)',
        backgroundColor: 'var(--icui-bg-secondary)'
      }}>
        <h1 style={{ margin: 0, color: 'var(--icui-accent)' }}>
          ICUI Test 8.1 - Explorer Multi-Select & Context Menus
        </h1>
        <p style={{ margin: '0.5rem 0 0', color: 'var(--icui-text-secondary)', fontSize: '0.9rem' }}>
          Testing Phase 8.1: Multi-select file operations, right-click context menus, and keyboard navigation.
        </p>
      </div>

      {/* Main content */}
      <div style={{ display: 'flex', height: 'calc(100vh - 120px)' }}>
        {/* Explorer Panel */}
        <div style={{
          width: '50%',
          borderRight: '1px solid var(--icui-border)',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            padding: '0.5rem',
            backgroundColor: 'var(--icui-bg-secondary)',
            borderBottom: '1px solid var(--icui-border)',
            fontSize: '0.9rem',
            fontWeight: 'bold'
          }}>
            📁 Enhanced Explorer with Multi-Select
          </div>
          <ICUIEnhancedExplorer
            onFileSelect={handleFileSelect}
            onFileDoubleClick={handleFileDoubleClick}
            onFileCreate={handleFileCreate}
            onFolderCreate={handleFolderCreate}
            onFileDelete={handleFileDelete}
            onFileRename={handleFileRename}
          />
        </div>

        {/* Info Panel */}
        <div style={{
          width: '50%',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Instructions */}
          <div style={{
            padding: '1rem',
            backgroundColor: 'var(--icui-bg-secondary)',
            borderBottom: '1px solid var(--icui-border)'
          }}>
            <h3 style={{ margin: '0 0 0.5rem', color: 'var(--icui-accent)' }}>
              🧪 Phase 8.1 Features
            </h3>
            <div style={{ fontSize: '0.85rem', lineHeight: '1.4' }}>
              <h4 style={{ margin: '0.5rem 0 0.25rem', color: 'var(--icui-text-primary)' }}>Multi-Select:</h4>
              <ul style={{ margin: '0', paddingLeft: '1rem', color: 'var(--icui-text-secondary)' }}>
                <li><kbd>Ctrl+Click</kbd> - Toggle individual selection</li>
                <li><kbd>Shift+Click</kbd> - Range selection</li>
                <li><kbd>Ctrl+A</kbd> - Select all files</li>
                <li><kbd>Esc</kbd> - Clear selection</li>
              </ul>

              <h4 style={{ margin: '0.5rem 0 0.25rem', color: 'var(--icui-text-primary)' }}>Context Menu:</h4>
              <ul style={{ margin: '0', paddingLeft: '1rem', color: 'var(--icui-text-secondary)' }}>
                <li><strong>Right-click</strong> on files/folders for context menu</li>
                <li>Copy, Cut, Paste operations</li>
                <li>Rename, Delete, Duplicate actions</li>
                <li>New File/Folder creation</li>
              </ul>

              <h4 style={{ margin: '0.5rem 0 0.25rem', color: 'var(--icui-text-primary)' }}>Keyboard Navigation:</h4>
              <ul style={{ margin: '0', paddingLeft: '1rem', color: 'var(--icui-text-secondary)' }}>
                <li><kbd>↑/↓</kbd> - Navigate files</li>
                <li><kbd>Shift+↑/↓</kbd> - Extend selection</li>
                <li><kbd>F2</kbd> - Rename selected file</li>
                <li><kbd>Delete</kbd> - Delete selected files</li>
              </ul>
            </div>
          </div>

          {/* Selected File Info */}
          <div style={{
            padding: '1rem',
            backgroundColor: 'var(--icui-bg-tertiary)',
            borderBottom: '1px solid var(--icui-border)'
          }}>
            <h4 style={{ margin: '0 0 0.5rem', color: 'var(--icui-accent)' }}>
              📋 Selected File
            </h4>
            {selectedFile ? (
              <div style={{ fontSize: '0.85rem' }}>
                <div><strong>Name:</strong> {selectedFile.name}</div>
                <div><strong>Type:</strong> {selectedFile.type}</div>
                <div><strong>Path:</strong> {selectedFile.path}</div>
                {selectedFile.size && <div><strong>Size:</strong> {selectedFile.size} bytes</div>}
                {selectedFile.modified && <div><strong>Modified:</strong> {selectedFile.modified}</div>}
              </div>
            ) : (
              <div style={{ color: 'var(--icui-text-secondary)', fontSize: '0.85rem' }}>
                No file selected. Click on a file to see details.
              </div>
            )}
          </div>

          {/* Activity Log */}
          <div style={{
            flex: 1,
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <h4 style={{ margin: '0 0 0.5rem', color: 'var(--icui-accent)' }}>
              📝 Activity Log
            </h4>
            <div style={{
              flex: 1,
              backgroundColor: 'var(--icui-bg-secondary)',
              border: '1px solid var(--icui-border)',
              borderRadius: '4px',
              padding: '0.5rem',
              overflow: 'auto',
              fontSize: '0.8rem',
              fontFamily: 'var(--icui-font-mono)'
            }}>
              {messages.length === 0 ? (
                <div style={{ color: 'var(--icui-text-secondary)' }}>
                  Activity will appear here as you interact with the explorer...
                </div>
              ) : (
                messages.map((message, index) => (
                  <div key={index} style={{ 
                    marginBottom: '0.25rem',
                    color: 'var(--icui-text-primary)'
                  }}>
                    {message}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '0.5rem 1rem',
        borderTop: '1px solid var(--icui-border)',
        backgroundColor: 'var(--icui-bg-secondary)',
        fontSize: '0.8rem',
        color: 'var(--icui-text-secondary)'
      }}>
        💡 Try right-clicking on files/folders, use Ctrl+Click for multi-select, and test keyboard shortcuts!
      </div>
    </div>
  );
};

export default ICUITest81;
