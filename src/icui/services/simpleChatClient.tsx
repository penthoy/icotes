/**
 * Simple Chat Client for debugging
 * Bypasses enhanced service and connects directly to /ws/chat
 */

export class SimpleChatClient {
  private ws: WebSocket | null = null;
  private connectionId: string = '';
  
  async connect(): Promise<boolean> {
    try {
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat`;
      console.log('[SimpleChatClient] Connecting to:', wsUrl);
      
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('[SimpleChatClient] Connected successfully');
        this.connectionId = Math.random().toString(36);
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[SimpleChatClient] Message received:', data);
        } catch (e) {
          console.log('[SimpleChatClient] Raw message:', event.data);
        }
      };
      
      this.ws.onclose = (event) => {
        console.log('[SimpleChatClient] Connection closed:', event.code, event.reason);
      };
      
      this.ws.onerror = (error) => {
        console.error('[SimpleChatClient] WebSocket error:', error);
      };
      
      return true;
    } catch (error) {
      console.error('[SimpleChatClient] Connection failed:', error);
      return false;
    }
  }
  
  async sendMessage(content: string): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    
    const message = {
      type: 'message',
      content: content,
      metadata: {
        session_id: 'test-session-' + Date.now(),
        agent_id: 'personal_agent',
        streaming: true,
        timestamp: new Date()
      }
    };
    
    console.log('[SimpleChatClient] Sending message:', message);
    this.ws.send(JSON.stringify(message));
  }
  
  disconnect(): void {
    if (this.ws) {
      console.log('[SimpleChatClient] Disconnecting...');
      this.ws.close();
      this.ws = null;
    }
  }
}

// Expose globally for testing
(window as any).SimpleChatClient = SimpleChatClient;
