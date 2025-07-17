/**
 * Integrated Home Component for Backend Integration Testing
 * 
 * This component is a backend-connected version of the original home.tsx
 * component, designed for integration testing and development. It replaces
 * local state management with backend-synchronized state.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { ICUIEditorFile } from '../../../src/icui/components/panels/ICUIEnhancedEditorPanel';
import { useBackendState } from '../../../src/hooks/useBackendState';
import { useBackendContext } from '../../../src/contexts/BackendContext';
import BackendConnectedExplorer from './BackendConnectedExplorer';
import BackendConnectedTerminal from './BackendConnectedTerminal';

/**
 * Connection Status Indicator
 */
const ConnectionStatus: React.FC = () => {
  const { connectionStatus, isConnected, isConnecting, error } = useBackendContext();
  
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'text-green-500';
      case 'connecting': return 'text-yellow-500';
      case 'disconnected': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };
  
  const getStatusText = () => {
    if (isConnecting) return 'Connecting...';
    if (isConnected) return 'Connected';
    if (error) return `Error: ${error}`;
    return 'Disconnected';
  };
  
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-2 h-2 rounded-full ${getStatusColor()}`}></div>
      <span className={`text-sm ${getStatusColor()}`}>
        {getStatusText()}
      </span>
    </div>
  );
};

/**
 * Backend Status Monitor
 */
const BackendStatus: React.FC = () => {
  const { workspaceState, files, terminals } = useBackendState();
  
  return (
    <div className="text-sm text-gray-600">
      <div>Files: {files.length}</div>
      <div>Terminals: {terminals.length}</div>
      <div>Workspace: {workspaceState?.name || 'Default'}</div>
    </div>
  );
};

/**
 * Test Controls
 */
const TestControls: React.FC = () => {
  const { actions } = useBackendState();
  const { connect, disconnect, isConnected } = useBackendContext();
  
  const handleCreateFile = useCallback(async () => {
    try {
      await actions.createFile('test-file.js', '// Test file created\nconsole.log("Hello from test file!");');
    } catch (error) {
      console.error('Failed to create file:', error);
    }
  }, [actions]);
  
  const handleCreateTerminal = useCallback(async () => {
    try {
      const newTerminal = await actions.createTerminal('Test Terminal');
      // Start the terminal to transition it to running state
      await actions.startTerminal(newTerminal.id);
    } catch (error) {
      console.error('Failed to create/start terminal:', error);
    }
  }, [actions]);
  
  const handleExecuteCode = useCallback(async () => {
    try {
      await actions.executeCode('test-file', 'console.log("Hello from integrated home!");', 'javascript');
    } catch (error) {
      console.error('Failed to execute code:', error);
    }
  }, [actions]);
  
  return (
    <div className="flex space-x-2">
      <button
        onClick={isConnected ? disconnect : connect}
        className={`px-3 py-1 rounded ${
          isConnected 
            ? 'bg-red-500 hover:bg-red-600 text-white' 
            : 'bg-green-500 hover:bg-green-600 text-white'
        }`}
      >
        {isConnected ? 'Disconnect' : 'Connect'}
      </button>
      
      <button
        onClick={handleCreateFile}
        disabled={!isConnected}
        className="px-3 py-1 rounded bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50"
      >
        Create File
      </button>
      
      <button
        onClick={handleCreateTerminal}
        disabled={!isConnected}
        className="px-3 py-1 rounded bg-purple-500 hover:bg-purple-600 text-white disabled:opacity-50"
      >
        Create Terminal
      </button>
      
      <button
        onClick={handleExecuteCode}
        disabled={!isConnected}
        className="px-3 py-1 rounded bg-orange-500 hover:bg-orange-600 text-white disabled:opacity-50"
      >
        Execute Code
      </button>
    </div>
  );
};

/**
 * File List Display
 */
const FileList: React.FC = () => {
  const { files } = useBackendState();
  
  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold mb-2">Files</h3>
      {files.length === 0 ? (
        <p className="text-gray-500">No files loaded</p>
      ) : (
        <ul className="space-y-1">
          {files.map((file) => (
            <li key={file.id} className="flex items-center space-x-2">
              <span className="text-sm font-mono">{file.name}</span>
              {file.modified && <span className="text-yellow-500">●</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

/**
 * Terminal List Display with Backend Terminal Integration
 */
const TerminalList: React.FC = () => {
  const { terminals, actions } = useBackendState();
  const [selectedTerminalId, setSelectedTerminalId] = useState<string | null>(null);
  const { isConnected } = useBackendContext();
  
  // Debug logging
  console.log('[TerminalList] Current state:', { 
    terminals: terminals.length, 
    selectedTerminalId, 
    isConnected,
    terminalDetails: terminals.map(t => ({ id: t.id, name: t.name, status: t.status }))
  });
  
  // Select first terminal if available and none selected
  useEffect(() => {
    if (terminals.length > 0 && !selectedTerminalId) {
      console.log('[TerminalList] Selecting first terminal:', terminals[0].id);
      setSelectedTerminalId(terminals[0].id);
    }
  }, [terminals, selectedTerminalId]);
  
  return (
    <div className="h-full flex flex-col">
      <div className="p-2 border-b bg-blue-100">
        <h3 className="text-sm font-semibold">Terminal List ({terminals.length})</h3>
        <div className="text-xs text-gray-600">Available terminals</div>
      </div>
      
      <div className="flex-1 flex flex-col">
        {terminals.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <p>No terminals created</p>
            <p className="text-xs mt-1">Terminal will be created automatically</p>
          </div>
        ) : (
          <>
            {/* Terminal List */}
            <div className="border-b">
              <div className="space-y-1 p-2">
                {terminals.map((terminal) => (
                  <div 
                    key={terminal.id} 
                    className={`cursor-pointer p-2 rounded text-sm ${
                      selectedTerminalId === terminal.id 
                        ? 'bg-blue-100 border-blue-300' 
                        : 'hover:bg-gray-100'
                    }`}
                    onClick={() => {
                      console.log('[TerminalList] Selecting terminal:', terminal.id);
                      setSelectedTerminalId(terminal.id);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono">{terminal.name || terminal.id}</span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        terminal.status === 'running' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {terminal.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Terminal Display - Always show if there's a selected terminal */}
            {selectedTerminalId && (
              <div className="flex-1 min-h-0">
                <div className="h-full border border-red-500 bg-yellow-100 p-2">
                  <div className="text-xs text-red-600 mb-2">
                    [DEBUG] Terminal container - selectedTerminalId: {selectedTerminalId}
                  </div>
                  <BackendConnectedTerminal 
                    terminalId={selectedTerminalId}
                    className="h-full"
                    onTerminalReady={(terminal) => console.log('[TerminalList] Terminal ready:', terminal)}
                    onTerminalOutput={(output) => console.log('[TerminalList] Terminal output:', output)}
                    onTerminalExit={(code) => console.log('[TerminalList] Terminal exit:', code)}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/**
 * Main Integrated Home Component
 */
export const IntegratedHome: React.FC = () => {
  const [theme, setTheme] = useState('dark');
  
  // Backend state
  const { 
    workspaceState, 
    files, 
    terminals, 
    actions,
    error: backendError 
  } = useBackendState();
  
  const { isConnected } = useBackendContext();
  
  // Debug logging for terminal state
  console.log('[IntegratedHome] Terminal state:', { 
    terminalsCount: terminals.length,
    terminals: terminals.map(t => ({ id: t.id, name: t.name, status: t.status })),
    isConnected
  });
  
  // Debug: log the first terminal details
  if (terminals.length > 0) {
    console.log('[IntegratedHome] First terminal details:', {
      id: terminals[0].id,
      name: terminals[0].name,
      status: terminals[0].status,
      type: typeof terminals[0].id
    });
  }
  
  // Auto-create terminal on load - but only ONCE
  useEffect(() => {
    const createInitialTerminal = async () => {
      if (isConnected && terminals.length === 0) {
        console.log('[IntegratedHome] Auto-creating initial terminal...');
        try {
          const newTerminal = await actions.createTerminal('Auto Terminal');
          console.log('[IntegratedHome] Initial terminal created successfully:', newTerminal);
          console.log('[IntegratedHome] Terminal ID:', newTerminal?.id);
          
          // Start the terminal to transition it to running state
          if (newTerminal && newTerminal.id) {
            console.log('[IntegratedHome] Starting terminal...');
            await actions.startTerminal(newTerminal.id);
            console.log('[IntegratedHome] Terminal started successfully');
          } else {
            console.error('[IntegratedHome] Terminal creation failed - no ID returned');
          }
        } catch (error) {
          console.error('[IntegratedHome] Failed to create/start initial terminal:', error);
          console.error('[IntegratedHome] Error details:', {
            message: error.message,
            stack: error.stack,
            name: error.name
          });
        }
      }
    };
    
    // Add a small delay to prevent race conditions
    const timeoutId = setTimeout(createInitialTerminal, 100);
    return () => clearTimeout(timeoutId);
  }, [isConnected, terminals.length, actions]);
  
  // Initialize workspace state from backend
  useEffect(() => {
    if (isConnected && workspaceState) {
      console.log('Workspace state updated:', workspaceState);
      
      // Update theme from backend preferences
      if (workspaceState.preferences?.theme) {
        setTheme(workspaceState.preferences.theme);
      }
    }
  }, [isConnected, workspaceState]);
  
  // Handle theme changes
  const handleThemeChange = useCallback((newTheme: string) => {
    setTheme(newTheme);
    
    // Sync to backend if connected
    if (isConnected) {
      actions.updateWorkspaceState({
        preferences: {
          theme: newTheme,
          font_size: 14,
          font_family: 'monospace',
          tab_size: 2,
          word_wrap: true,
          line_numbers: true,
          auto_save: true,
          auto_save_delay: 1000
        }
      }).catch(console.error);
    }
  }, [isConnected, actions]);
  
  // File operations
  const handleFileCreate = useCallback(async (path: string, content: string = '') => {
    try {
      await actions.createFile(path, content);
    } catch (error) {
      console.error('Failed to create file:', error);
    }
  }, [actions]);
  
  const handleFileUpdate = useCallback(async (fileId: string, content: string) => {
    try {
      await actions.updateFile(fileId, content);
    } catch (error) {
      console.error('Failed to update file:', error);
    }
  }, [actions]);
  
  const handleFileDelete = useCallback(async (fileId: string) => {
    try {
      await actions.deleteFile(fileId);
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  }, [actions]);
  
  // Terminal operations
  const handleTerminalCreate = useCallback(async (name?: string) => {
    try {
      const newTerminal = await actions.createTerminal(name);
      // Start the terminal to transition it to running state
      await actions.startTerminal(newTerminal.id);
    } catch (error) {
      console.error('Failed to create/start terminal:', error);
    }
  }, [actions]);
  
  const handleTerminalInput = useCallback(async (terminalId: string, input: string) => {
    try {
      await actions.sendTerminalInput(terminalId, input);
    } catch (error) {
      console.error('Failed to send terminal input:', error);
    }
  }, [actions]);
  
  return (
    <div className={`integrated-home ${theme} h-screen flex flex-col`}>
      <header className="bg-gray-800 text-white p-2">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-bold">Terminal Integration Test</h1>
          <ConnectionStatus />
        </div>
      </header>
      
      <main className="flex-1 overflow-hidden flex">
        {/* Left Panel - Controls */}
        <div className="w-1/4 bg-gray-100 border-r flex flex-col">
          <div className="h-1/3 border-b">
            <BackendConnectedExplorer 
              className="h-full"
              onFileSelect={(file) => console.log('File selected:', file)}
            />
          </div>
          <div className="h-2/3">
            <TerminalList />
          </div>
        </div>
        
        {/* Right Panel - Main Terminal Display */}
        <div className="flex-1 flex flex-col">
          {/* Status Bar */}
          <div className="p-2 bg-blue-50 border-b">
            <div className="flex justify-between items-center text-sm">
              <div className="flex space-x-4">
                <span><strong>Connection:</strong> {isConnected ? 'Connected' : 'Disconnected'}</span>
                <span><strong>Files:</strong> {files.length}</span>
                <span><strong>Terminals:</strong> {terminals.length}</span>
                <span><strong>Workspace:</strong> {workspaceState?.name || 'Default'}</span>
              </div>
              <div className="text-xs text-gray-600">
                Testing URL: http://192.168.2.195:8000/integration
              </div>
            </div>
          </div>
          
          {/* Main Terminal Area */}
          <div className="flex-1 flex flex-col">
            {terminals.length === 0 ? (
              <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <div className="text-gray-500 mb-4">No terminals available</div>
                  <button
                    onClick={() => handleTerminalCreate('Main Terminal')}
                    disabled={!isConnected}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                  >
                    Create Terminal
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 min-h-0">
                <div className="h-full border-2 border-green-500 bg-green-50 p-1">
                  <div className="text-xs text-green-600 mb-1 font-bold">
                    [DEBUG] MAIN TERMINAL DISPLAY - {terminals.length} terminal(s) available
                  </div>
                  <BackendConnectedTerminal 
                    terminalId={terminals[0].id}
                    className="h-full"
                    onTerminalReady={(terminal) => console.log('[IntegratedHome] Main terminal ready:', terminal)}
                    onTerminalOutput={(output) => console.log('[IntegratedHome] Main terminal output:', output)}
                    onTerminalExit={(code) => console.log('[IntegratedHome] Main terminal exit:', code)}
                  />
                </div>
              </div>
            )}
          </div>
          
          {/* Control Panel */}
          <div className="p-4 bg-gray-50 border-t">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-md font-medium mb-2">Theme Control</h3>
                <select 
                  value={theme} 
                  onChange={(e) => handleThemeChange(e.target.value)}
                  className="px-3 py-1 border rounded"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="blue">Blue</option>
                  <option value="green">Green</option>
                  <option value="purple">Purple</option>
                </select>
              </div>
              
              <div>
                <h3 className="text-md font-medium mb-2">Quick Actions</h3>
                <div className="space-y-2">
                  <button
                    onClick={() => handleTerminalCreate('Additional Terminal')}
                    disabled={!isConnected}
                    className="block w-full px-3 py-1 text-sm rounded bg-purple-500 hover:bg-purple-600 text-white disabled:opacity-50"
                  >
                    Create Additional Terminal
                  </button>
                  <button
                    onClick={() => handleFileCreate('test.py', 'print("Hello from Python!")')}
                    disabled={!isConnected}
                    className="block w-full px-3 py-1 text-sm rounded bg-green-500 hover:bg-green-600 text-white disabled:opacity-50"
                  >
                    Create Test File
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <footer className="bg-gray-800 text-white p-2">
        <div className="flex justify-between items-center">
          <BackendStatus />
          <TestControls />
        </div>
        {backendError && (
          <div className="mt-2 text-red-400 text-sm">
            Error: {backendError}
          </div>
        )}
      </footer>
    </div>
  );
};
