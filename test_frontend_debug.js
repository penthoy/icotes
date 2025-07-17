// Test frontend debug terminal integration
// Run this in browser dev console to debug

// First, let's check if we can access the backend
fetch('http://localhost:8000/api/terminals')
  .then(response => response.json())
  .then(data => {
    console.log('Backend terminals:', data);
    
    // Now try to create a terminal
    return fetch('http://localhost:8000/api/terminals', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ name: 'browser-test' })
    });
  })
  .then(response => response.json())
  .then(data => {
    console.log('Created terminal:', data);
    
    // Start the terminal
    const terminalId = data.data.id;
    return fetch(`http://localhost:8000/api/terminals/${terminalId}/start`, {
      method: 'POST'
    });
  })
  .then(response => response.json())
  .then(data => {
    console.log('Started terminal:', data);
    
    // Try to connect via WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/terminal/${terminalId}');
    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => console.log('WebSocket message:', event.data);
    ws.onerror = (error) => console.error('WebSocket error:', error);
    ws.onclose = () => console.log('WebSocket closed');
  })
  .catch(error => {
    console.error('Error:', error);
  });
