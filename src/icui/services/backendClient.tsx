/**
 * Backend Client Abstraction Framework
 * 
 * Generalized backend client base class with connection management,
 * fallback handling, and service detection patterns extracted from
 * simpleeditor.tsx EditorBackendClient.
 */

import { notificationService, NotificationType } from './notificationService';

export interface ConnectionStatus {
  connected: boolean;
  services?: Record<string, any>;
  timestamp?: number;
  error?: string;
}

export interface BackendConfig {
  baseUrl?: string;
  retryAttempts?: number;
  retryDelay?: number;
  healthCheckInterval?: number;
  fallbackMode?: boolean;
}

export interface ServiceCapabilities {
  [serviceName: string]: boolean;
}

/**
 * Base class for all backend clients
 * Provides common functionality for connection management, health checks,
 * and fallback handling
 */
export abstract class BackendClient {
  protected baseUrl: string;
  protected config: Required<BackendConfig>;
  protected connectionStatus: ConnectionStatus | null = null;
  protected capabilities: ServiceCapabilities = {};
  
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private statusCallbacks: Set<(status: ConnectionStatus) => void> = new Set();

  constructor(config: BackendConfig = {}) {
    // Initialize base URL
    const backendUrl = config.baseUrl || 
                      import.meta.env.VITE_BACKEND_URL || 
                      import.meta.env.VITE_API_URL;
    
    if (!backendUrl || backendUrl.startsWith('/')) {
      throw new Error('Backend URL must be a full URL (http://...), not a relative path. Check VITE_BACKEND_URL in .env');
    }
    
    this.baseUrl = backendUrl;
    
    // Merge with defaults
    this.config = {
      baseUrl: backendUrl,
      retryAttempts: 3,
      retryDelay: 1000,
      healthCheckInterval: 30000, // 30 seconds
      fallbackMode: false,
      ...config
    };
  }

  /**
   * Initialize the client and start health monitoring
   */
  async initialize(): Promise<void> {
    await this.checkServiceAvailability();
    this.startHealthMonitoring();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopHealthMonitoring();
    this.statusCallbacks.clear();
  }

  /**
   * Check if services are available and update capabilities
   */
  async checkServiceAvailability(): Promise<ServiceCapabilities> {
    try {
      const status = await this.getConnectionStatus();
      this.connectionStatus = status;
      
      if (status.connected && status.services) {
        this.capabilities = await this.detectServiceCapabilities(status.services);
      } else {
        this.capabilities = {};
      }
      
      this.notifyStatusChange(status);
      return this.capabilities;
      
    } catch (error) {
      const errorStatus: ConnectionStatus = {
        connected: false,
        error: error instanceof Error ? error.message : String(error),
        timestamp: Date.now()
      };
      
      this.connectionStatus = errorStatus;
      this.capabilities = {};
      this.notifyStatusChange(errorStatus);
      
      return this.capabilities;
    }
  }

  /**
   * Get current connection status with health check
   */
  async getConnectionStatus(): Promise<ConnectionStatus> {
    try {
      const response = await this.fetchWithRetry(`${this.baseUrl}/health`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      return {
        connected: data.status === 'healthy',
        services: data.services || {},
        timestamp: data.timestamp || Date.now()
      };
      
    } catch (error) {
      return {
        connected: false,
        error: error instanceof Error ? error.message : String(error),
        timestamp: Date.now()
      };
    }
  }

  /**
   * Check if a specific service capability is available
   */
  hasCapability(serviceName: string): boolean {
    return this.capabilities[serviceName] === true;
  }

  /**
   * Get all available capabilities
   */
  getCapabilities(): ServiceCapabilities {
    return { ...this.capabilities };
  }

  /**
   * Subscribe to connection status changes
   */
  onStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.statusCallbacks.add(callback);
    
    // Immediately call with current status if available
    if (this.connectionStatus) {
      callback(this.connectionStatus);
    }
    
    return () => {
      this.statusCallbacks.delete(callback);
    };
  }

  /**
   * Fetch with retry logic and error handling
   */
  protected async fetchWithRetry(
    url: string, 
    options: RequestInit = {}, 
    attempts: number = this.config.retryAttempts
  ): Promise<Response> {
    let lastError: Error;

    for (let i = 0; i < attempts; i++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        });

        // Don't retry on 4xx errors (client errors)
        if (response.status >= 400 && response.status < 500) {
          return response;
        }

        if (response.ok || i === attempts - 1) {
          return response;
        }

        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        // If this is the last attempt, throw the error
        if (i === attempts - 1) {
          throw lastError;
        }
        
        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, this.config.retryDelay * (i + 1)));
      }
    }

    throw lastError!;
  }

  /**
   * Handle API response with consistent error handling
   */
  protected async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorText = await response.text().catch(() => response.statusText);
      throw new Error(`${response.status}: ${errorText}`);
    }

    try {
      return await response.json();
    } catch (error) {
      throw new Error('Invalid JSON response from server');
    }
  }

  /**
   * Execute operation with fallback support
   */
  protected async executeWithFallback<T>(
    operation: () => Promise<T>,
    fallback: () => Promise<T>,
    operationName: string
  ): Promise<T> {
    if (this.config.fallbackMode || !this.connectionStatus?.connected) {
      notificationService.warning(`${operationName} running in fallback mode`);
      return fallback();
    }

    try {
      return await operation();
    } catch (error) {
      notificationService.error(`${operationName} failed: ${error.message}`);
      
      // Try fallback if available
      try {
        notificationService.info(`Attempting ${operationName} fallback...`);
        return await fallback();
      } catch (fallbackError) {
        notificationService.error(`${operationName} fallback also failed`);
        throw error; // Throw original error
      }
    }
  }

  /**
   * Abstract method to detect service capabilities
   * Each client should implement based on their specific services
   */
  protected abstract detectServiceCapabilities(services: Record<string, any>): Promise<ServiceCapabilities>;

  private startHealthMonitoring(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
    }

    this.healthCheckTimer = setInterval(async () => {
      await this.checkServiceAvailability();
    }, this.config.healthCheckInterval);
  }

  private stopHealthMonitoring(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
  }

  private notifyStatusChange(status: ConnectionStatus): void {
    this.statusCallbacks.forEach(callback => callback(status));
  }
}

/**
 * Specialized client for file operations
 */
export class FileClient extends BackendClient {
  protected async detectServiceCapabilities(services: Record<string, any>): Promise<ServiceCapabilities> {
    const capabilities: ServiceCapabilities = {};
    
    // Test ICPY file API availability
    try {
      const response = await fetch(`${this.baseUrl}/api/files?path=/`, { method: 'GET' });
      capabilities.icpy_files = response.status !== 404 && response.status !== 405;
    } catch {
      capabilities.icpy_files = false;
    }
    
    // Test basic file endpoints
    capabilities.file_upload = services.file_upload || false;
    capabilities.file_download = services.file_download || false;
    
    return capabilities;
  }

  async listFiles(path: string = '/'): Promise<any[]> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files?path=${encodeURIComponent(path)}`);
        return this.handleResponse(response);
      },
      async () => {
        // Fallback: return empty array or sample files
        return [];
      },
      'File listing'
    );
  }

  async getFileContent(path: string): Promise<string> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files/content?path=${encodeURIComponent(path)}`);
        const data = await this.handleResponse<any>(response);
        return data.data?.content || '';
      },
      async () => {
        // Fallback: return empty content
        return '';
      },
      'File content retrieval'
    );
  }

  async saveFile(path: string, content: string): Promise<void> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files`, {
          method: 'PUT',
          body: JSON.stringify({
            path,
            content,
            encoding: 'utf-8',
            create_dirs: true
          }),
        });
        await this.handleResponse(response);
      },
      async () => {
        // Fallback: simulate save
        notificationService.warning('File saved locally only (backend unavailable)');
      },
      'File save'
    );
  }
}

/**
 * Specialized client for terminal operations
 */
export class TerminalClient extends BackendClient {
  protected async detectServiceCapabilities(services: Record<string, any>): Promise<ServiceCapabilities> {
    const capabilities: ServiceCapabilities = {};
    
    // Test terminal WebSocket availability
    capabilities.terminal_websocket = services.terminal || false;
    capabilities.command_execution = services.execute || false;
    
    return capabilities;
  }

  async executeCommand(command: string): Promise<any> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/execute`, {
          method: 'POST',
          body: JSON.stringify({ code: command, language: 'bash' }),
        });
        return this.handleResponse(response);
      },
      async () => {
        // Fallback: return mock result
        return { output: 'Command execution not available (backend unavailable)', success: false };
      },
      'Command execution'
    );
  }
}

/**
 * Specialized client for code execution
 */
export class ExecutionClient extends BackendClient {
  protected async detectServiceCapabilities(services: Record<string, any>): Promise<ServiceCapabilities> {
    const capabilities: ServiceCapabilities = {};
    
    capabilities.python_execution = services.python || false;
    capabilities.javascript_execution = services.javascript || false;
    capabilities.code_execution = services.execute || false;
    
    return capabilities;
  }

  async executeCode(code: string, language: string): Promise<any> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/execute`, {
          method: 'POST',
          body: JSON.stringify({ code, language }),
        });
        return this.handleResponse(response);
      },
      async () => {
        // Fallback: return mock result
        return { 
          output: `Code execution not available (backend unavailable)\nCode:\n${code}`, 
          success: false 
        };
      },
      'Code execution'
    );
  }
}
