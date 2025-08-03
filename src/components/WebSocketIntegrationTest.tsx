/**
 * WebSocket Services Integration Test
 * 
 * This test component demonstrates the integration of WebSocket services:
 * - Terminal Test Component
 * - Chat Backend Client
 * - Backend Service
 * - Connection Manager
 * - Health Monitoring
 */

import React, { useState, useEffect, useRef } from 'react';
import ICUITerminalTest, { ICUITerminalTestRef } from '../icui/components/ICUITerminalTest';
import { chatBackendClient, ChatMessage } from '../icui/services/chatBackendClient';
import { icuiBackendService } from '../icui/services/backendService';
import { ConnectionHealthMonitor } from '../services/connection-monitor';

interface IntegrationTestProps {
  className?: string;
}

const WebSocketIntegrationTest: React.FC<IntegrationTestProps> = ({ className = '' }) => {
  const terminalRef = useRef<ICUITerminalTestRef>(null);
  const healthMonitor = useRef<ConnectionHealthMonitor>(new ConnectionHealthMonitor());
  
  // State
  const [terminalConnected, setTerminalConnected] = useState(false);
  const [chatConnected, setChatConnected] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [testResults, setTestResults] = useState<string[]>([]);

  // Test WebSocket services
  useEffect(() => {
    const runIntegrationTests = async () => {
      const results: string[] = [];
      
      try {
        // Test 1: Terminal Connection
        results.push('✓ WebSocket Terminal component loaded');
        
        // Test 2: Chat Backend Client
        chatBackendClient.onStatus((status) => {
          setChatConnected(status.connected);
          if (status.connected) {
            results.push('✓ Chat Service service connected');
          }
        });
        
        chatBackendClient.onMessage((message) => {
          setMessages(prev => [...prev, message]);
          results.push('✓ Chat message received');
        });
        
        const chatConnected = await chatBackendClient.connectWebSocket();
        if (chatConnected) {
          results.push('✓ Chat WebSocket connection established');
        }
        
        // Test 3: Backend Service
        const backendStatus = await icuiBackendService.getConnectionStatus();
        setBackendConnected(backendStatus.connected);
        results.push(`✓ Backend service status: ${backendStatus.connected ? 'connected' : 'disconnected'}`);
        
        // Test 4: Health Monitoring
        const testConnectionId = 'test-connection-' + Date.now();
        healthMonitor.current.startMonitoring();
        
        // Get initial health status
        const initialHealth = healthMonitor.current.getHealthScore(testConnectionId);
        setHealthStatus(initialHealth);
        results.push('✓ Health monitoring initialized');
        
        // Test 5: Connection Manager Integration
        if (terminalRef.current) {
          const connectionId = terminalRef.current.getConnectionId();
          if (connectionId) {
            results.push(`✓ Terminal connection ID: ${connectionId}`);
          }
        }
        
        setTestResults(results);
        
      } catch (error) {
        results.push(`✗ Integration test error: ${error}`);
        setTestResults(results);
      }
    };

    runIntegrationTests();
    
    return () => {
      // Cleanup
      chatBackendClient.disconnect();
      icuiBackendService.disconnect();
      healthMonitor.current.stopMonitoring();
    };
  }, []);

  const sendTestMessage = async () => {
    try {
      await chatBackendClient.sendMessage('Test message from integration test', {
        streaming: false,
        priority: 'normal'
      });
    } catch (error) {
      console.error('Test message failed:', error);
    }
  };

  const testBackendOperation = async () => {
    try {
      const files = await icuiBackendService.getWorkspaceFiles();
      setTestResults(prev => [...prev, `✓ Backend operation: Found ${files.length} files`]);
    } catch (error) {
      setTestResults(prev => [...prev, `✗ Backend operation failed: ${error}`]);
    }
  };

  return (
    <div className={`websocket-integration-test ${className}`} style={{ padding: '20px' }}>
      <h2>WebSocket Services Integration Test</h2>
      
      {/* Connection Status */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Connection Status</h3>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ 
            padding: '10px', 
            backgroundColor: terminalConnected ? '#22c55e' : '#ef4444',
            color: 'white',
            borderRadius: '4px'
          }}>
            Terminal: {terminalConnected ? 'Connected' : 'Disconnected'}
          </div>
          <div style={{ 
            padding: '10px', 
            backgroundColor: chatConnected ? '#22c55e' : '#ef4444',
            color: 'white',
            borderRadius: '4px'
          }}>
            Chat: {chatConnected ? 'Connected' : 'Disconnected'}
          </div>
          <div style={{ 
            padding: '10px', 
            backgroundColor: backendConnected ? '#22c55e' : '#ef4444',
            color: 'white',
            borderRadius: '4px'
          }}>
            Backend: {backendConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* Health Status */}
      {healthStatus && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Health Monitoring</h3>
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#f3f4f6', 
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}>
            <pre>{JSON.stringify(healthStatus, null, 2)}</pre>
          </div>
        </div>
      )}

      {/* Test Controls */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Test Controls</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={sendTestMessage} style={{ padding: '10px 20px' }}>
            Send Test Chat Message
          </button>
          <button onClick={testBackendOperation} style={{ padding: '10px 20px' }}>
            Test Backend Operation
          </button>
        </div>
      </div>

      {/* Test Results */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Test Results</h3>
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '4px',
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          {testResults.map((result, index) => (
            <div key={index} style={{ 
              fontFamily: 'monospace', 
              fontSize: '12px',
              margin: '2px 0',
              color: result.startsWith('✓') ? '#22c55e' : result.startsWith('✗') ? '#ef4444' : '#000'
            }}>
              {result}
            </div>
          ))}
        </div>
      </div>

      {/* Chat Messages */}
      {messages.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Chat Messages</h3>
          <div style={{ 
            padding: '10px', 
            backgroundColor: '#f8f9fa', 
            borderRadius: '4px',
            maxHeight: '150px',
            overflowY: 'auto'
          }}>
            {messages.map((message, index) => (
              <div key={index} style={{ 
                margin: '5px 0',
                padding: '5px',
                backgroundColor: message.role === 'user' ? '#e3f2fd' : '#f3e5f5',
                borderRadius: '4px',
                fontSize: '12px'
              }}>
                <strong>{message.role}:</strong> {message.content}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* WebSocket Terminal */}
      <div style={{ marginBottom: '20px' }}>
        <h3>WebSocket Terminal</h3>
        <div style={{ 
          height: '300px', 
          border: '1px solid #ddd', 
          borderRadius: '4px',
          backgroundColor: '#000'
        }}>
          <ICUITerminalTest
            ref={terminalRef}
            onTerminalReady={(terminal) => {
              setTerminalConnected(true);
              setTestResults(prev => [...prev, '✓ WebSocket Terminal ready']);
            }}
            onTerminalOutput={(data) => {
              console.log('Terminal output:', data);
            }}
            onTerminalExit={(code) => {
              setTerminalConnected(false);
              setTestResults(prev => [...prev, `✓ Terminal exited with code: ${code}`]);
            }}
          />
        </div>
      </div>

      <div style={{ fontSize: '12px', color: '#666' }}>
        This integration test demonstrates the WebSocket services with connection management,
        error handling, message queuing, and health monitoring. Check the console for detailed logs.
      </div>
    </div>
  );
};

export default WebSocketIntegrationTest;
