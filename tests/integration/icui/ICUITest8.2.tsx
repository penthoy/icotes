/**
 * ICUI Test 8.2 - Explorer Extensibility
 * 
 * Tests Step 8.2: Explorer extensibility with arbitrary functions,
 * custom commands, and dynamic menu groups.
 */

import React, { useEffect, useState } from 'react';
import ICUIEnhancedExplorer from '../../../src/icui/components/panels/ICUIEnhancedExplorer';
import { 
  registerExplorerCommand, 
  createCustomMenuGroup, 
  ExplorerMenuExtensions,
  ExplorerMenuContext 
} from '../../../src/icui/components/explorer/ExplorerContextMenu';
import { ICUIFileNode } from '../../../src/icui/services';
import { log } from '../../../src/services/frontend-logger';

/**
 * Example custom commands for Explorer extensibility
 */
const registerCustomCommands = () => {
  // Custom command: Show file info
  registerExplorerCommand(
    'explorer.showFileInfo',
    'Show File Info',
    async (context: ExplorerMenuContext) => {
      const files = context.selectedFiles;
      if (files.length === 0) return;
      
      const fileInfo = files.map(file => ({
        name: file.name,
        path: file.path,
        type: file.type,
        size: file.size || 'Unknown',
        modified: file.modified || 'Unknown'
      }));
      
      alert(`File Info:\n${JSON.stringify(fileInfo, null, 2)}`);
      log.info('CustomCommand', 'Showed file info', { files: fileInfo });
    },
    {
      icon: 'ℹ️',
      shortcut: 'Ctrl+I',
      description: 'Display detailed information about selected files',
    }
  );

  // Custom command: Duplicate with timestamp
  registerExplorerCommand(
    'explorer.duplicateWithTimestamp',
    'Duplicate with Timestamp',
    async (context: ExplorerMenuContext) => {
      const files = context.selectedFiles;
      if (files.length === 0) return;
      
      for (const file of files) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const newName = `${file.name}_${timestamp}`;
        console.log(`Would duplicate ${file.name} as ${newName}`);
        log.info('CustomCommand', 'Duplicated with timestamp', { original: file.name, copy: newName });
      }
      
      alert(`Duplicated ${files.length} file(s) with timestamp`);
    },
    {
      icon: '📋',
      shortcut: 'Ctrl+Shift+D',
      description: 'Create copies of selected files with timestamp suffix',
    }
  );

  // Custom command: Open in external editor
  registerExplorerCommand(
    'explorer.openExternal',
    'Open in External Editor',
    async (context: ExplorerMenuContext) => {
      const files = context.selectedFiles.filter(f => f.type === 'file');
      if (files.length === 0) {
        alert('No files selected for external editing');
        return;
      }
      
      for (const file of files) {
        console.log(`Would open ${file.path} in external editor`);
        log.info('CustomCommand', 'Opened in external editor', { file: file.path });
      }
      
      alert(`Opened ${files.length} file(s) in external editor`);
    },
    {
      icon: '🚀',
      description: 'Open selected files in external editor',
    }
  );

  // Custom command: Archive selected items
  registerExplorerCommand(
    'explorer.archive',
    'Create Archive',
    async (context: ExplorerMenuContext) => {
      const files = context.selectedFiles;
      if (files.length === 0) return;
      
      const archiveName = `archive_${new Date().toISOString().split('T')[0]}.zip`;
      console.log(`Would create archive ${archiveName} with:`, files.map(f => f.name));
      log.info('CustomCommand', 'Created archive', { archive: archiveName, files: files.length });
      
      alert(`Created archive ${archiveName} with ${files.length} item(s)`);
    },
    {
      icon: '📦',
      shortcut: 'Ctrl+Shift+A',
      description: 'Create ZIP archive of selected files and folders',
    }
  );
};

const ICUITest82: React.FC = () => {
  const [messages, setMessages] = useState<string[]>([]);

  const addMessage = (message: string) => {
    setMessages(prev => [...prev.slice(-10), `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  useEffect(() => {
    // Register custom commands when component mounts
    registerCustomCommands();
    log.info('ICUITest8.2', 'Registered custom Explorer commands');
    addMessage('Custom Explorer commands registered');
  }, []);

  // Create custom menu groups with ordering
  const developerGroup = createCustomMenuGroup(
    'developer-tools',
    [
      {
        id: 'explorer.showFileInfo',
        label: 'Show File Info',
        icon: 'ℹ️',
        shortcut: 'Ctrl+I',
        commandId: 'explorer.showFileInfo',
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'explorer.openExternal',
        label: 'Open in External Editor',
        icon: '🚀',
        commandId: 'explorer.openExternal',
        isVisible: () => true,
        isEnabled: () => true,
      }
    ],
    {
      label: 'Developer Tools',
      separator: true,
      position: 'after',
      anchor: 'paste',
      priority: 10,
    }
  );

  const archiveGroup = createCustomMenuGroup(
    'archive-tools',
    [
      {
        id: 'explorer.duplicateWithTimestamp',
        label: 'Duplicate with Timestamp',
        icon: '📋',
        shortcut: 'Ctrl+Shift+D',
        commandId: 'explorer.duplicateWithTimestamp',
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'explorer.archive',
        label: 'Create Archive',
        icon: '📦',
        shortcut: 'Ctrl+Shift+A',
        commandId: 'explorer.archive',
        isVisible: () => true,
        isEnabled: () => true,
      }
    ],
    {
      label: 'Archive & Backup',
      separator: true,
      position: 'before',
      anchor: 'selectAll',
      priority: 20,
    }
  );

  // Configure extensions for the Explorer
  const explorerExtensions: ExplorerMenuExtensions = {
    customGroups: [developerGroup, archiveGroup],
    customCommands: [
      'explorer.showFileInfo',
      'explorer.duplicateWithTimestamp', 
      'explorer.openExternal',
      'explorer.archive'
    ],
    // Example: Hide some default items
    // hiddenItems: ['duplicate'] // Uncomment to hide the default duplicate command
  };

  return (
    <div style={{
      height: '100vh',
      backgroundColor: '#1a1a1a',
      color: 'white',
      display: 'flex',
      flexDirection: 'column'
    }}>
      <div style={{
        padding: '20px',
        borderBottom: '1px solid #333',
        backgroundColor: '#2a2a2a'
      }}>
        <h1 style={{ margin: '0 0 10px 0', fontSize: '24px' }}>
          ICUI Test 8.2 - Explorer Extensibility
        </h1>
        <p style={{ margin: '0 0 15px 0', color: '#ccc' }}>
          This test demonstrates Step 8.2: Explorer extensibility with custom commands and menu groups.
        </p>
        
        <div style={{ marginBottom: '15px' }}>
          <strong>Custom Commands Added:</strong>
          <ul style={{ margin: '5px 0 0 20px', color: '#aaa' }}>
            <li>Show File Info (Ctrl+I) - Display file details</li>
            <li>Duplicate with Timestamp (Ctrl+Shift+D) - Copy with timestamp</li>
            <li>Open in External Editor - Launch external editor</li>
            <li>Create Archive (Ctrl+Shift+A) - ZIP selected items</li>
          </ul>
        </div>
        
        <div style={{ marginBottom: '15px' }}>
          <strong>Custom Menu Groups:</strong>
          <ul style={{ margin: '5px 0 0 20px', color: '#aaa' }}>
            <li>Developer Tools (after Paste command)</li>
            <li>Archive & Backup (before Select All)</li>
          </ul>
        </div>
        
        <div style={{ color: '#ffeb3b' }}>
          <strong>Test Instructions:</strong>
          <ul style={{ margin: '5px 0 0 20px' }}>
            <li>1. Select one or more files/folders</li>
            <li>2. Right-click to open context menu</li>
            <li>3. Look for custom menu groups and items</li>
            <li>4. Try the keyboard shortcuts (Ctrl+I, Ctrl+Shift+D, Ctrl+Shift+A)</li>
            <li>5. Check console and message log for command execution</li>
          </ul>
        </div>

        {/* Messages Log */}
        <div style={{ marginTop: '15px' }}>
          <strong>Activity Log:</strong>
          <div style={{
            height: '80px',
            overflowY: 'auto',
            backgroundColor: '#1a1a1a',
            border: '1px solid #444',
            padding: '5px',
            fontSize: '12px',
            fontFamily: 'monospace'
          }}>
            {messages.length === 0 ? (
              <div style={{ color: '#666' }}>No activity yet...</div>
            ) : (
              messages.map((msg, i) => (
                <div key={i} style={{ color: '#4CAF50' }}>{msg}</div>
              ))
            )}
          </div>
        </div>
      </div>
      
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ICUIEnhancedExplorer
          className="h-full"
          extensions={explorerExtensions}
          onFileSelect={(file: ICUIFileNode) => {
            addMessage(`File selected: ${file.name}`);
            log.info('ICUITest8.2', 'File selected', { file: file.name });
          }}
          onFileDoubleClick={(file: ICUIFileNode) => {
            addMessage(`File double-clicked: ${file.name}`);
            log.info('ICUITest8.2', 'File double-clicked', { file: file.name });
          }}
          onFileCreate={(path: string) => {
            addMessage(`File created: ${path}`);
          }}
          onFolderCreate={(path: string) => {
            addMessage(`Folder created: ${path}`);
          }}
          onFileDelete={(path: string) => {
            addMessage(`Deleted: ${path}`);
          }}
          onFileRename={(oldPath: string, newPath: string) => {
            addMessage(`Renamed: ${oldPath} → ${newPath}`);
          }}
        />
      </div>
    </div>
  );
};

export default ICUITest82;
