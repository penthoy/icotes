/**
 * Integration Test Environment
 * 
 * Main integration test component for ICUI-ICPY integration testing.
 * Provides a comprehensive testing environment with connection status,
 * backend communication testing, and component integration verification.
 */

import React from 'react';
import { BackendContextProvider } from '../../src/contexts/BackendContext';
import { IntegratedHome } from './components/IntegratedHome';

/**
 * Main Integration Test Component
 */
export const Integration: React.FC = () => {
  return (
    <BackendContextProvider>
      <div className="integration-test-environment">
        <IntegratedHome />
      </div>
    </BackendContextProvider>
  );
};

export default Integration;

import React from 'react';
import { BackendContextProvider } from '../../src/contexts/BackendContext';
import { IntegratedHome } from './components/IntegratedHome';

/**
 * Main Integration Test Component
 */
export const Integration: React.FC = () => {
  return (
    <BackendContextProvider>
      <div className="integration-test-environment">
        <IntegratedHome />
      </div>
    </BackendContextProvider>
  );
};

export default Integration;

// Test Controls Component
const TestControls: React.FC = () => {
  const [wsService] = useState(() => getWebSocketService());
  const [backendClient] = useState(() => getBackendClient());
  const [testResults, setTestResults] = useState<Record<string, any>>({});

  const runConnectionTest = useCallback(async () => {
    console.log('Running connection test...');
    try {
      await wsService.connect();
      const health = await backendClient.getHealth();
      setTestResults(prev => ({
        ...prev,
        connectionTest: { success: true, data: health }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        connectionTest: { success: false, error: error.message }
      }));
    }
  }, [wsService, backendClient]);

  const runWorkspaceTest = useCallback(async () => {
    console.log('Running workspace test...');
    try {
      const workspaceState = await backendClient.getWorkspaceState();
      setTestResults(prev => ({
        ...prev,
        workspaceTest: { success: true, data: workspaceState }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        workspaceTest: { success: false, error: error.message }
      }));
    }
  }, [backendClient]);

  const runFileSystemTest = useCallback(async () => {
    console.log('Running file system test...');
    try {
      const directoryTree = await backendClient.getDirectoryTree('/');
      setTestResults(prev => ({
        ...prev,
        fileSystemTest: { success: true, data: directoryTree }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        fileSystemTest: { success: false, error: error.message }
      }));
    }
  }, [backendClient]);

  const runTerminalTest = useCallback(async () => {
    console.log('Running terminal test...');
    try {
      const terminals = await backendClient.getTerminals();
      setTestResults(prev => ({
        ...prev,
        terminalTest: { success: true, data: terminals }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        terminalTest: { success: false, error: error.message }
      }));
    }
  }, [backendClient]);

  const clearResults = useCallback(() => {
    setTestResults({});
  }, []);

  return (
    <div className="test-controls">
      <h3>Test Controls</h3>
      <div className="test-buttons">
        <button onClick={runConnectionTest}>Test Connection</button>
        <button onClick={runWorkspaceTest}>Test Workspace</button>
        <button onClick={runFileSystemTest}>Test File System</button>
        <button onClick={runTerminalTest}>Test Terminal</button>
        <button onClick={clearResults}>Clear Results</button>
      </div>
      
      <div className="test-results">
        <h4>Test Results</h4>
        <pre>{JSON.stringify(testResults, null, 2)}</pre>
      </div>
    </div>
  );
};

// Connection Status Component
const ConnectionStatus: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [statistics, setStatistics] = useState<any>({});
  const [wsService] = useState(() => getWebSocketService());

  useEffect(() => {
    const updateStatus = (data: { status: ConnectionStatus }) => {
      setConnectionStatus(data.status);
    };

    wsService.on('connection_status_changed', updateStatus);
    
    // Update statistics periodically
    const statsInterval = setInterval(() => {
      setStatistics(wsService.getStatistics());
    }, 1000);

    return () => {
      wsService.off('connection_status_changed', updateStatus);
      clearInterval(statsInterval);
    };
  }, [wsService]);

  const getStatusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'connected': return 'green';
      case 'connecting': return 'yellow';
      case 'disconnected': return 'red';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  return (
    <div className="connection-status">
      <h3>Connection Status</h3>
      <div className="status-indicator">
        <span 
          className="status-dot" 
          style={{ backgroundColor: getStatusColor(connectionStatus) }}
        />
        <span className="status-text">{connectionStatus}</span>
      </div>
      
      <div className="statistics">
        <h4>Statistics</h4>
        <ul>
          <li>Messages Sent: {statistics.messages_sent || 0}</li>
          <li>Messages Received: {statistics.messages_received || 0}</li>
          <li>Reconnect Count: {statistics.reconnect_count || 0}</li>
          <li>Latency: {statistics.latency || 0}ms</li>
          <li>Uptime: {statistics.uptime || 0}ms</li>
        </ul>
      </div>
    </div>
  );
};

// Backend Status Component
const BackendStatus: React.FC = () => {
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [backendStats, setBackendStats] = useState<any>(null);
  const [backendClient] = useState(() => getBackendClient());

  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const health = await backendClient.getHealth();
        setBackendHealth(health);
      } catch (error) {
        setBackendHealth({ error: error.message });
      }
    };

    const checkBackendStats = async () => {
      try {
        const stats = await backendClient.getStatistics();
        setBackendStats(stats);
      } catch (error) {
        setBackendStats({ error: error.message });
      }
    };

    // Check initially
    checkBackendHealth();
    checkBackendStats();

    // Check periodically
    const healthInterval = setInterval(checkBackendHealth, 5000);
    const statsInterval = setInterval(checkBackendStats, 10000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(statsInterval);
    };
  }, [backendClient]);

  return (
    <div className="backend-status">
      <h3>Backend Status</h3>
      
      <div className="health-status">
        <h4>Health</h4>
        <pre>{JSON.stringify(backendHealth, null, 2)}</pre>
      </div>
      
      <div className="backend-statistics">
        <h4>Statistics</h4>
        <pre>{JSON.stringify(backendStats, null, 2)}</pre>
      </div>
    </div>
  );
};

// Message Monitor Component
const MessageMonitor: React.FC = () => {
  const [messages, setMessages] = useState<any[]>([]);
  const [maxMessages, setMaxMessages] = useState(50);
  const [wsService] = useState(() => getWebSocketService());

  useEffect(() => {
    const handleMessage = (data: any) => {
      setMessages(prev => {
        const newMessages = [...prev, {
          timestamp: new Date().toISOString(),
          type: 'received',
          data
        }];
        return newMessages.slice(-maxMessages);
      });
    };

    // Subscribe to all events (this is for debugging)
    const eventTypes = [
      'connected',
      'disconnected',
      'error',
      'reconnecting',
      'max_reconnects_reached',
      'workspace.state_changed',
      'filesystem.file_changed',
      'terminal.output',
      'terminal.session_created',
      'terminal.session_closed'
    ];

    eventTypes.forEach(event => {
      wsService.on(event, handleMessage);
    });

    return () => {
      eventTypes.forEach(event => {
        wsService.off(event, handleMessage);
      });
    };
  }, [wsService, maxMessages]);

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <div className="message-monitor">
      <h3>Message Monitor</h3>
      <div className="monitor-controls">
        <button onClick={clearMessages}>Clear Messages</button>
        <label>
          Max Messages: 
          <input 
            type="number" 
            value={maxMessages} 
            onChange={e => setMaxMessages(Number(e.target.value))}
            min="10"
            max="200"
          />
        </label>
      </div>
      
      <div className="messages-list">
        {messages.map((message, index) => (
          <div key={index} className="message-item">
            <span className="timestamp">{message.timestamp}</span>
            <span className="type">{message.type}</span>
            <pre className="data">{JSON.stringify(message.data, null, 2)}</pre>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main Integration Component
export const Integration: React.FC = () => {
  const [wsService] = useState(() => getWebSocketService());
  const [backendClient] = useState(() => getBackendClient());

  useEffect(() => {
    // Auto-connect on mount
    wsService.connect().catch(error => {
      console.error('Failed to connect:', error);
    });

    return () => {
      wsService.disconnect();
    };
  }, [wsService]);

  return (
    <div className="integration-test-environment">
      <header className="test-header">
        <h1>ICUI-ICPY Integration Test Environment</h1>
        <p>Phase 1.1: WebSocket Service Layer Testing</p>
      </header>
      
      <main className="test-main">
        <div className="test-grid">
          <div className="test-section">
            <ConnectionStatus />
          </div>
          
          <div className="test-section">
            <BackendStatus />
          </div>
          
          <div className="test-section">
            <TestControls />
          </div>
          
          <div className="test-section full-width">
            <MessageMonitor />
          </div>
        </div>
      </main>
      
      <footer className="test-footer">
        <p>Integration Test Environment - Phase 1.1 Complete</p>
      </footer>
      
      <style jsx>{`
        .integration-test-environment {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .test-header {
          text-align: center;
          margin-bottom: 30px;
          padding: 20px;
          background: #f5f5f5;
          border-radius: 8px;
        }
        
        .test-main {
          margin-bottom: 20px;
        }
        
        .test-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        
        .test-section {
          background: white;
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
        }
        
        .test-section.full-width {
          grid-column: 1 / -1;
        }
        
        .test-section h3 {
          margin-top: 0;
          color: #333;
        }
        
        .test-buttons {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        
        .test-buttons button {
          padding: 8px 16px;
          background: #007bff;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        
        .test-buttons button:hover {
          background: #0056b3;
        }
        
        .test-results {
          background: #f8f9fa;
          padding: 15px;
          border-radius: 4px;
          max-height: 300px;
          overflow-y: auto;
        }
        
        .test-results pre {
          margin: 0;
          font-size: 12px;
          white-space: pre-wrap;
        }
        
        .status-indicator {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 15px;
        }
        
        .status-dot {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }
        
        .status-text {
          font-weight: bold;
          text-transform: capitalize;
        }
        
        .statistics ul {
          list-style: none;
          padding: 0;
        }
        
        .statistics li {
          padding: 2px 0;
          font-size: 14px;
        }
        
        .health-status, .backend-statistics {
          margin-bottom: 15px;
        }
        
        .health-status pre, .backend-statistics pre {
          background: #f8f9fa;
          padding: 10px;
          border-radius: 4px;
          font-size: 12px;
          max-height: 150px;
          overflow-y: auto;
        }
        
        .monitor-controls {
          display: flex;
          gap: 15px;
          align-items: center;
          margin-bottom: 15px;
        }
        
        .monitor-controls button {
          padding: 6px 12px;
          background: #28a745;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        
        .monitor-controls input {
          width: 60px;
          padding: 4px;
          margin-left: 5px;
        }
        
        .messages-list {
          max-height: 400px;
          overflow-y: auto;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        
        .message-item {
          border-bottom: 1px solid #eee;
          padding: 10px;
          font-size: 12px;
        }
        
        .message-item:last-child {
          border-bottom: none;
        }
        
        .timestamp {
          color: #666;
          margin-right: 10px;
        }
        
        .type {
          color: #007bff;
          font-weight: bold;
          margin-right: 10px;
        }
        
        .data {
          margin: 5px 0 0 0;
          background: #f8f9fa;
          padding: 5px;
          border-radius: 2px;
          white-space: pre-wrap;
        }
        
        .test-footer {
          text-align: center;
          padding: 20px;
          background: #f5f5f5;
          border-radius: 8px;
          color: #666;
        }
      `}</style>
    </div>
  );
};

export default Integration;
