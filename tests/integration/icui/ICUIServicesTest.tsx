/**
 * Test implementation demonstrating ICUI Service Framework
 * Tests Phase 5.1 (Notification Service) and 5.2 (Backend Client Abstraction)
 */

import React, { useEffect, useState } from 'react';
import { useNotifications } from '../../../src/icui/services/notificationService';
import { FileClient, TerminalClient, ExecutionClient, ConnectionStatus } from '../../../src/icui/services/backendClient';

const ICUIServicesTest: React.FC = () => {
  const notifications = useNotifications();
  const [fileClient] = useState(() => new FileClient());
  const [terminalClient] = useState(() => new TerminalClient());
  const [executionClient] = useState(() => new ExecutionClient());
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, boolean>>({});
  const [files, setFiles] = useState<any[]>([]);

  useEffect(() => {
    // Initialize clients and set up status monitoring
    const initializeClients = async () => {
      try {
        await fileClient.initialize();
        await terminalClient.initialize();
        await executionClient.initialize();
        
        notifications.success('ICUI services initialized successfully');
      } catch (error) {
        notifications.error(`Failed to initialize services: ${error.message}`);
      }
    };

    // Subscribe to connection status changes
    const unsubscribe = fileClient.onStatusChange((status) => {
      setConnectionStatus(status);
      setCapabilities(fileClient.getCapabilities());
    });

    initializeClients();

    return () => {
      unsubscribe();
      fileClient.destroy();
      terminalClient.destroy();
      executionClient.destroy();
    };
  }, [fileClient, terminalClient, executionClient, notifications]);

  const testNotifications = () => {
    notifications.info('This is an info notification');
    setTimeout(() => notifications.success('Success notification test'), 500);
    setTimeout(() => notifications.warning('Warning notification test'), 1000);
    setTimeout(() => notifications.error('Error notification test'), 1500);
  };

  const testFileOperations = async () => {
    try {
      notifications.info('Testing file operations...');
      const fileList = await fileClient.listFiles('/home/penthoy/ilaborcode/workspace');
      // Handle both array and object response formats
      const filesArray = Array.isArray(fileList) ? fileList : ((fileList as any)?.data || []);
      setFiles(filesArray);
      notifications.success(`Found ${filesArray.length} files`);
    } catch (error) {
      notifications.error(`File operation failed: ${error.message}`);
    }
  };

  const testCodeExecution = async () => {
    try {
      notifications.info('Testing code execution...');
      const result = await executionClient.executeCode('print("Hello from ICUI!")', 'python');
      notifications.success('Code executed successfully');
      console.log('Execution result:', result);
    } catch (error) {
      notifications.error(`Code execution failed: ${error.message}`);
    }
  };

  const testTerminalCommand = async () => {
    try {
      notifications.info('Testing terminal command...');
      const result = await terminalClient.executeCommand('echo "Hello from terminal!"');
      notifications.success('Terminal command executed');
      console.log('Terminal result:', result);
    } catch (error) {
      notifications.error(`Terminal command failed: ${error.message}`);
    }
  };

  return (
    <div className="p-6 space-y-6 bg-white dark:bg-gray-900 min-h-screen">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
        ICUI Services Test (Phase 5.1 & 5.2)
      </h1>

      {/* Connection Status */}
      <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
          Connection Status
        </h2>
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${connectionStatus?.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
            <span className="text-gray-700 dark:text-gray-300">
              Status: {connectionStatus?.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          {connectionStatus?.error && (
            <div className="text-red-600 dark:text-red-400">
              Error: {connectionStatus.error}
            </div>
          )}
          {connectionStatus?.timestamp && (
            <div className="text-gray-500 dark:text-gray-400">
              Last checked: {new Date(connectionStatus.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Service Capabilities */}
      <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
          Service Capabilities
        </h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(capabilities).map(([capability, available]) => (
            <div key={capability} className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${available ? 'bg-green-500' : 'bg-gray-400'}`}></span>
              <span className="text-gray-700 dark:text-gray-300">
                {capability}: {available ? 'Available' : 'Unavailable'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Test Buttons */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          onClick={testNotifications}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
        >
          Test Notifications
        </button>
        
        <button
          onClick={testFileOperations}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
        >
          Test File Ops
        </button>
        
        <button
          onClick={testCodeExecution}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
        >
          Test Code Execution
        </button>
        
        <button
          onClick={testTerminalCommand}
          className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
        >
          Test Terminal
        </button>
      </div>

      {/* Active Notifications Display */}
      {notifications.notifications.length > 0 && (
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
            Active Notifications ({notifications.notifications.length})
          </h2>
          <div className="space-y-2 text-sm max-h-40 overflow-y-auto">
            {notifications.notifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-2 rounded flex justify-between items-center ${
                  notification.type === 'success' ? 'bg-green-100 text-green-800' :
                  notification.type === 'error' ? 'bg-red-100 text-red-800' :
                  notification.type === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-blue-100 text-blue-800'
                }`}
              >
                <span>{notification.message}</span>
                <button
                  onClick={() => notifications.dismiss(notification.id)}
                  className="text-xs opacity-70 hover:opacity-100 font-bold"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={notifications.clear}
            className="mt-2 px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
          >
            Clear All
          </button>
        </div>
      )}

      {/* Files List */}
      {files.length > 0 && (
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">
            Files in Workspace ({files.length})
          </h2>
          <div className="text-sm space-y-1 max-h-60 overflow-y-auto">
            {files.map((file, index) => (
              <div key={index} className="text-gray-700 dark:text-gray-300 font-mono">
                📄 {file.name || file.path}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
        <h2 className="text-lg font-semibold mb-2 text-blue-900 dark:text-blue-100">
          ICUI Services Framework Features
        </h2>
        <ul className="text-sm space-y-1 text-blue-800 dark:text-blue-200">
          <li>✅ <strong>Phase 5.1:</strong> Unified notification system with toast UI</li>
          <li>✅ <strong>Phase 5.2:</strong> Backend client abstraction with fallback support</li>
          <li>✅ Connection status monitoring and health checks</li>
          <li>✅ Service capability detection</li>
          <li>✅ Automatic retry logic and error handling</li>
          <li>✅ React hooks integration for notifications</li>
          <li>✅ Graceful degradation when backend is unavailable</li>
        </ul>
      </div>
    </div>
  );
};

export default ICUIServicesTest;
