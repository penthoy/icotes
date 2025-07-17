/**
 * WebSocket Mock for Testing
 * 
 * Provides mock WebSocket implementation for testing ICUI-ICPY integration
 * without requiring a real backend connection. Includes message simulation,
 * connection state management, and event handling.
 */

// Mock vitest if not available
const vi = {
  fn: (mockFn?: any) => mockFn || (() => {})
};

import type { WebSocketMessage, JsonRpcRequest, JsonRpcResponse } from '../../../src/types/backend-types';

export class MockWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  public readyState: number = MockWebSocket.CONNECTING;
  public url: string;
  public protocol: string = '';
  public extensions: string = '';
  public binaryType: BinaryType = 'blob';
  public bufferedAmount: number = 0;

  public onopen: ((this: WebSocket, ev: Event) => any) | null = null;
  public onclose: ((this: WebSocket, ev: CloseEvent) => any) | null = null;
  public onmessage: ((this: WebSocket, ev: MessageEvent) => any) | null = null;
  public onerror: ((this: WebSocket, ev: Event) => any) | null = null;

  private messageQueue: WebSocketMessage[] = [];
  private responses: Map<string, any> = new Map();
  private subscriptions: Set<string> = new Set();

  constructor(url: string, protocols?: string | string[]) {
    this.url = url;
    
    // Simulate connection delay
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen.call(this as any, new Event('open'));
      }
    }, 100);
  }

  /**
   * Send a message to the mock WebSocket
   */
  send(data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }

    try {
      const message: WebSocketMessage = JSON.parse(data as string);
      this.messageQueue.push(message);
      
      // Handle different message types
      if (message.type === 'json-rpc' && message.payload) {
        this.handleJsonRpcMessage(message.payload);
      } else if (message.type === 'ping') {
        this.handlePingMessage(message.payload);
      }
    } catch (error) {
      console.error('Failed to parse mock WebSocket message:', error);
    }
  }

  /**
   * Close the mock WebSocket connection
   */
  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSING;
    
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        const closeEvent = new CloseEvent('close', {
          code: code || 1000,
          reason: reason || 'Normal closure'
        });
        this.onclose.call(this as any, closeEvent);
      }
    }, 10);
  }

  /**
   * Add event listeners (for compatibility)
   */
  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    // Basic implementation for testing
    if (type === 'open' && typeof listener === 'function') {
      this.onopen = listener as any;
    } else if (type === 'close' && typeof listener === 'function') {
      this.onclose = listener as any;
    } else if (type === 'message' && typeof listener === 'function') {
      this.onmessage = listener as any;
    } else if (type === 'error' && typeof listener === 'function') {
      this.onerror = listener as any;
    }
  }

  /**
   * Remove event listeners (for compatibility)
   */
  removeEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    if (type === 'open' && this.onopen === listener) {
      this.onopen = null;
    } else if (type === 'close' && this.onclose === listener) {
      this.onclose = null;
    } else if (type === 'message' && this.onmessage === listener) {
      this.onmessage = null;
    } else if (type === 'error' && this.onerror === listener) {
      this.onerror = null;
    }
  }

  /**
   * Simulate receiving a message from the server
   */
  receiveMessage(message: WebSocketMessage): void {
    if (this.readyState === MockWebSocket.OPEN && this.onmessage) {
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(message)
      });
      this.onmessage.call(this as any, messageEvent);
    }
  }

  /**
   * Simulate connection error
   */
  simulateError(error?: Error): void {
    if (this.onerror) {
      const errorEvent = new ErrorEvent('error', {
        error: error || new Error('Mock WebSocket error')
      });
      this.onerror.call(this as any, errorEvent as any);
    }
  }

  /**
   * Handle JSON-RPC messages
   */
  private handleJsonRpcMessage(payload: JsonRpcRequest): void {
    if (payload.id) {
      // It's a request, send back a response
      const response: JsonRpcResponse = {
        jsonrpc: '2.0',
        id: payload.id,
        result: this.generateMockResponse(payload.method, payload.params)
      };

      setTimeout(() => {
        this.receiveMessage({ type: 'json-rpc', payload: response });
      }, 50);
    } else {
      // It's a notification, handle subscription
      if (payload.method === 'subscribe' && payload.params?.topic) {
        this.subscriptions.add(payload.params.topic);
      } else if (payload.method === 'unsubscribe' && payload.params?.topic) {
        this.subscriptions.delete(payload.params.topic);
      }
    }
  }

  /**
   * Handle ping messages
   */
  private handlePingMessage(payload: any): void {
    setTimeout(() => {
      this.receiveMessage({
        type: 'pong',
        payload: { timestamp: payload.timestamp }
      });
    }, 10);
  }

  /**
   * Generate mock responses based on method
   */
  private generateMockResponse(method: string, params?: any): any {
    switch (method) {
      case 'workspace.get_state':
        return {
          id: 'workspace-1',
          name: 'Test Workspace',
          description: 'Mock workspace for testing',
          created_at: new Date().toISOString(),
          last_accessed: new Date().toISOString(),
          files: [
            {
              id: 'file-1',
              name: 'test.js',
              path: '/test.js',
              content: 'console.log("Hello, World!");',
              language: 'javascript',
              modified: false,
              created_at: new Date().toISOString(),
              last_modified: new Date().toISOString(),
              size: 29,
              is_active: true
            }
          ],
          panels: [],
          terminals: [],
          layout: {
            id: 'layout-1',
            name: 'Default',
            panels: [],
            created_at: new Date().toISOString(),
            is_default: true
          },
          preferences: {
            theme: 'github-dark',
            font_size: 14,
            font_family: 'Monaco',
            tab_size: 2,
            word_wrap: true,
            line_numbers: true,
            auto_save: true,
            auto_save_delay: 1500
          },
          statistics: {
            files_count: 1,
            terminals_count: 0,
            panels_count: 0,
            total_characters: 29,
            total_lines: 1,
            last_updated: new Date().toISOString()
          }
        };

      case 'filesystem.get_directory_tree':
        return {
          path: '/',
          name: 'root',
          type: 'directory',
          children: [
            {
              path: '/test.js',
              name: 'test.js',
              type: 'file',
              size: 29,
              modified_at: new Date().toISOString()
            },
            {
              path: '/src',
              name: 'src',
              type: 'directory',
              children: [
                {
                  path: '/src/app.js',
                  name: 'app.js',
                  type: 'file',
                  size: 150,
                  modified_at: new Date().toISOString()
                }
              ],
              modified_at: new Date().toISOString()
            }
          ],
          modified_at: new Date().toISOString()
        };

      case 'terminal.create_session':
        return {
          id: 'terminal-1',
          name: 'Terminal 1',
          command: '/bin/bash',
          cwd: '/',
          env: {},
          created_at: new Date().toISOString(),
          last_used: new Date().toISOString(),
          is_active: true,
          pid: 1234,
          status: 'running'
        };

      case 'file.create':
        return {
          id: 'file-new',
          name: params?.name || 'new-file.js',
          path: params?.path || '/new-file.js',
          content: params?.content || '',
          language: params?.language || 'javascript',
          modified: false,
          created_at: new Date().toISOString(),
          last_modified: new Date().toISOString(),
          size: (params?.content || '').length,
          is_active: false
        };

      default:
        return { success: true, message: `Mock response for ${method}` };
    }
  }

  /**
   * Get all sent messages
   */
  getSentMessages(): WebSocketMessage[] {
    return [...this.messageQueue];
  }

  /**
   * Clear message queue
   */
  clearMessages(): void {
    this.messageQueue = [];
  }

  /**
   * Get subscriptions
   */
  getSubscriptions(): Set<string> {
    return new Set(this.subscriptions);
  }

  /**
   * Simulate backend events
   */
  simulateEvent(eventType: string, data: any): void {
    if (this.subscriptions.has(eventType)) {
      this.receiveMessage({
        type: 'event',
        payload: { type: eventType, data }
      });
    }
  }
}

// Mock fetch for HTTP client testing
export const mockFetch = vi.fn();

// Setup mock WebSocket
export const setupMockWebSocket = () => {
  // @ts-ignore
  global.WebSocket = MockWebSocket;
  global.fetch = mockFetch;
  
  // Reset mock fetch responses
  mockFetch.mockReset();
  
  // Default successful responses
  mockFetch.mockImplementation((url: string, options?: RequestInit) => {
    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true, data: `Mock response for ${url}` })
    });
  });
};

// Cleanup mock WebSocket
export const cleanupMockWebSocket = () => {
  // @ts-ignore
  global.WebSocket = undefined;
  // @ts-ignore
  global.fetch = undefined;
  mockFetch.mockReset();
};

export default MockWebSocket;
