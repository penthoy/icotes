// Debug script to test WebSocket connection in production
const ws = new WebSocket('ws://192.168.2.203:8000/ws');

ws.onopen = function() {
    console.log('✅ WebSocket connected successfully');
    
    // Subscribe to filesystem events
    const subscribeMessage = {
        type: 'subscribe',
        topics: ['fs.file_created', 'fs.file_deleted', 'fs.file_moved'],
        id: 'debug-test-' + Date.now()
    };
    
    ws.send(JSON.stringify(subscribeMessage));
    console.log('📡 Subscription message sent:', subscribeMessage);
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('📥 Received message:', message);
    
    if (message.type === 'filesystem_event') {
        console.log('🔥 FILESYSTEM EVENT DETECTED:', message.data);
    }
};

ws.onerror = function(error) {
    console.error('❌ WebSocket error:', error);
};

ws.onclose = function(event) {
    console.log('🔌 WebSocket closed:', event.code, event.reason);
};

// Keep the connection alive for testing
setTimeout(() => {
    console.log('⏰ Test completed');
    ws.close();
}, 30000);
