export interface CodeExecutionRequest {
  code: string;
  language: string;
}

export interface CodeExecutionResponse {
  output: string[];
  errors: string[];
  execution_time: number;
}

export interface WebSocketMessage {
  type: 'execute_code' | 'ping' | 'pong' | 'execution_result' | 'echo';
  code?: string;
  language?: string;
  output?: string[];
  errors?: string[];
  execution_time?: number;
  message?: string;
}

export class CodeExecutorWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.handleReconnect();
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(console.error);
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  executeCode(code: string, language: string = 'python'): Promise<CodeExecutionResponse> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const message: WebSocketMessage = {
        type: 'execute_code',
        code,
        language
      };

      // Set up one-time listener for the response
      const handleMessage = (event: MessageEvent) => {
        try {
          const response: WebSocketMessage = JSON.parse(event.data);
          
          if (response.type === 'execution_result') {
            this.ws?.removeEventListener('message', handleMessage);
            resolve({
              output: response.output || [],
              errors: response.errors || [],
              execution_time: response.execution_time || 0
            });
          }
        } catch (error) {
          this.ws?.removeEventListener('message', handleMessage);
          reject(error);
        }
      };

      this.ws.addEventListener('message', handleMessage);

      // Send the execution request
      this.ws.send(JSON.stringify(message));

      // Set a timeout for the execution
      setTimeout(() => {
        this.ws?.removeEventListener('message', handleMessage);
        reject(new Error('Code execution timeout'));
      }, 30000); // 30 second timeout
    });
  }

  ping(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket is not connected'));
        return;
      }

      const message: WebSocketMessage = { type: 'ping' };

      const handleMessage = (event: MessageEvent) => {
        try {
          const response: WebSocketMessage = JSON.parse(event.data);
          
          if (response.type === 'pong') {
            this.ws?.removeEventListener('message', handleMessage);
            resolve();
          }
        } catch (error) {
          this.ws?.removeEventListener('message', handleMessage);
          reject(error);
        }
      };

      this.ws.addEventListener('message', handleMessage);
      this.ws.send(JSON.stringify(message));

      // Timeout for ping
      setTimeout(() => {
        this.ws?.removeEventListener('message', handleMessage);
        reject(new Error('Ping timeout'));
      }, 5000);
    });
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  onMessage(callback: (message: WebSocketMessage) => void) {
    if (this.ws) {
      this.ws.addEventListener('message', (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          callback(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      });
    }
  }
}

// Fallback to REST API if WebSocket is not available
export class CodeExecutorREST {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async executeCode(code: string, language: string = 'python'): Promise<CodeExecutionResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, language }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Failed to execute code: ${error}`);
    }
  }

  async health(): Promise<{ status: string; connections: number }> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Failed to check health: ${error}`);
    }
  }
}

// Combined executor that tries WebSocket first, falls back to REST
export class CodeExecutor {
  private wsExecutor: CodeExecutorWebSocket;
  private restExecutor: CodeExecutorREST;
  private useWebSocket: boolean = true;

  constructor(wsUrl?: string, restUrl?: string) {
    this.wsExecutor = new CodeExecutorWebSocket(wsUrl);
    this.restExecutor = new CodeExecutorREST(restUrl);
  }

  async connect(): Promise<void> {
    try {
      await this.wsExecutor.connect();
      this.useWebSocket = true;
    } catch (error) {
      console.warn('WebSocket connection failed, falling back to REST API:', error);
      this.useWebSocket = false;
    }
  }

  async executeCode(code: string, language: string = 'python'): Promise<CodeExecutionResponse> {
    if (this.useWebSocket && this.wsExecutor.isConnected()) {
      try {
        return await this.wsExecutor.executeCode(code, language);
      } catch (error) {
        console.warn('WebSocket execution failed, falling back to REST API:', error);
        this.useWebSocket = false;
      }
    }

    return await this.restExecutor.executeCode(code, language);
  }

  disconnect() {
    this.wsExecutor.disconnect();
  }

  isConnected(): boolean {
    return this.useWebSocket ? this.wsExecutor.isConnected() : true;
  }

  onMessage(callback: (message: WebSocketMessage) => void) {
    this.wsExecutor.onMessage(callback);
  }
}
