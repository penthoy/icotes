import React, { useEffect, useState } from 'react';

const TestTerminal: React.FC = () => {
  const [status, setStatus] = useState('Initializing...');
  
  useEffect(() => {
    console.log('TestTerminal component mounted');
    setStatus('Attempting to connect...');
    
    const terminalId = Math.random().toString(36).substring(7);
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    let wsUrl: string;
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      wsUrl = `${protocol}//localhost:8000/ws/terminal/${terminalId}`;
    } else {
      wsUrl = `${protocol}//${window.location.hostname}:8000/ws/terminal/${terminalId}`;
    }
    
    console.log('Connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setStatus('Connected!');
    };
    
    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setStatus(`Disconnected: ${event.code} - ${event.reason}`);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('Connection error');
    };
    
    return () => {
      ws.close();
    };
  }, []);
  
  return (
    <div className="p-4 bg-black text-green-400 font-mono">
      <div>Test Terminal</div>
      <div>Status: {status}</div>
    </div>
  );
};

export default TestTerminal;
