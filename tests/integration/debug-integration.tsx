/**
 * Debug Integration Test
 * 
 * Minimal test component to debug the integration issues
 */

import React, { useState, useEffect } from 'react';

const DebugIntegration: React.FC = () => {
  const [status, setStatus] = useState('Loading...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      setStatus('Component mounted successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, []);

  const testBackendConnection = async () => {
    try {
      setStatus('Testing backend connection...');
      
      // Test the backend health endpoint
      const response = await fetch('http://192.168.2.195:8000/health');
      if (response.ok) {
        const data = await response.json();
        setStatus(`Backend connected: ${JSON.stringify(data)}`);
      } else {
        setError(`Backend connection failed: ${response.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Debug Integration Test</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h3>Status: {status}</h3>
        {error && (
          <div style={{ color: 'red' }}>
            <h3>Error: {error}</h3>
          </div>
        )}
      </div>

      <div style={{ marginBottom: '20px' }}>
        <button onClick={testBackendConnection}>Test Backend Connection</button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Debug Info:</h3>
        <ul>
          <li>Frontend URL: {window.location.href}</li>
          <li>Backend URL: http://192.168.2.195:8000</li>
          <li>WebSocket URL: ws://192.168.2.195:8000/ws/enhanced</li>
          <li>Current Time: {new Date().toISOString()}</li>
        </ul>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Component Test:</h3>
        <div style={{ border: '1px solid #ccc', padding: '10px' }}>
          This is a test div to verify the component is rendering correctly.
        </div>
      </div>
    </div>
  );
};

export default DebugIntegration;
