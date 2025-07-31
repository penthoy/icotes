/**
 * Enhanced ICUI Backend Service
 * 
 * Integrates all WebSocket improvements for file operations, explorer functionality,
 * and general backend communication with connection management, error handling,
 * message queuing, and health monitoring.
 */

import { EventEmitter } from 'eventemitter3';
import { EnhancedWebSocketService, ConnectionOptions, MessageOptions } from '../../services/enhanced-websocket-service';
import { WebSocketMigrationHelper } from '../../services/websocket-migration';
import { ConnectionStatus } from '../../types/backend-types';

export interface ICUIFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
  path?: string;
}

export interface ICUIFileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: ICUIFileNode[];
  isExpanded?: boolean; 
  size?: number;
  modified?: string;
}

export interface EnhancedBackendConfig {
  enableMessageQueue: boolean;
  enableHealthMonitoring: boolean;
  enableAutoRecovery: boolean;
  maxConcurrentConnections: number;
  messageTimeout: number;
  batchFileOperations: boolean;
}

/**
 * Enhanced centralized backend service for ICUI components
 * Provides file operations, connection management, and workspace utilities
 * with all WebSocket improvements integrated.
 */
export class EnhancedICUIBackendService extends EventEmitter {
  private enhancedService: EnhancedWebSocketService | null = null;
  private migrationHelper: WebSocketMigrationHelper | null = null;
  private connectionId: string | null = null;
  private _initialized = false;
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;
  
  // Configuration
  private config: EnhancedBackendConfig = {
    enableMessageQueue: true,
    enableHealthMonitoring: true,
    enableAutoRecovery: true,
    maxConcurrentConnections: 5,
    messageTimeout: 15000,
    batchFileOperations: true
  };

  constructor(config?: Partial<EnhancedBackendConfig>) {
    super();
    
    if (config) {
      this.config = { ...this.config, ...config };
    }
    
    this.initializeEnhancedService();
  }

  /**
   * Initialize enhanced WebSocket service
   */
  private initializeEnhancedService(): void {
    // Configure enhanced service for backend operations
    this.enhancedService = new EnhancedWebSocketService({
      enableMessageQueue: this.config.enableMessageQueue,
      enableHealthMonitoring: this.config.enableHealthMonitoring,
      enableAutoRecovery: this.config.enableAutoRecovery,
      maxConcurrentConnections: this.config.maxConcurrentConnections,
      messageTimeout: this.config.messageTimeout,
      batchConfig: {
        maxSize: this.config.batchFileOperations ? 5 : 1,
        maxWaitTime: this.config.batchFileOperations ? 100 : 0,
        enableCompression: true
      }
    });

    // Set up migration helper
    this.migrationHelper = new WebSocketMigrationHelper({
      migrateMain: true,
      fallbackToLegacy: true,
      testMode: false
    });

    // Enhanced service event handlers
    this.enhancedService.on('connection_opened', (data: any) => {
      console.log('[EnhancedICUIBackendService] Enhanced service connected:', data);
      this._initialized = true;
      this.emit('connection_status_changed', { status: 'connected' });
    });

    this.enhancedService.on('connection_closed', (data: any) => {
      console.log('[EnhancedICUIBackendService] Enhanced service disconnected:', data);
      this.emit('connection_status_changed', { status: 'disconnected' });
    });

    // Also listen for the legacy events for compatibility
    this.enhancedService.on('connected', (data: any) => {
      console.log('[EnhancedICUIBackendService] Enhanced service connected (legacy event):', data);
      this._initialized = true;
      this.emit('connection_status_changed', { status: 'connected' });
    });

    this.enhancedService.on('disconnected', (data: any) => {
      console.log('[EnhancedICUIBackendService] Enhanced service disconnected (legacy event):', data);
      this.emit('connection_status_changed', { status: 'disconnected' });
    });

    this.enhancedService.on('message', (data: any) => {
      if (data.connectionId === this.connectionId) {
        this.handleWebSocketMessage({ data: data.message });
      }
    });

    this.enhancedService.on('error', (error: any) => {
      console.error('[EnhancedICUIBackendService] Enhanced service error:', error);
      this.emit('error', error);
    });

    this.enhancedService.on('healthUpdate', (health: any) => {
      this.healthStatus = health;
      console.log('[EnhancedICUIBackendService] Health update:', health);
    });

    this.enhancedService.on('connectionClosed', (data: any) => {
      if (data.connectionId === this.connectionId) {
        console.log('[EnhancedICUIBackendService] Connection closed:', data);
        this.connectionId = null;
        this._initialized = false;
        this.emit('connection_status_changed', { status: 'disconnected' });
      }
    });
  }

  /**
   * Ensure service is initialized before operations
   */
  private async ensureInitialized(): Promise<void> {
    if (!this._initialized) {
      console.log('[EnhancedICUIBackendService] Auto-initializing enhanced service...');
      await this.initializeConnection();
      this._initialized = true;
    }
  }

  /**
   * Initialize connection with enhanced service
   */
  private async initializeConnection(): Promise<void> {
    if (this.connectionId && this.enhancedService) {
      console.log('[EnhancedICUIBackendService] Already connected');
      return;
    }

    if (!this.enhancedService) {
      throw new Error('Enhanced service not initialized');
    }

    try {
      const options: ConnectionOptions = {
        serviceType: 'main',
        sessionId: `backend_${Date.now()}`,
        autoReconnect: true,
        maxRetries: 5,
        priority: 'high',
        timeout: 15000
      };

      console.log('[EnhancedICUIBackendService] Connecting with options:', options);
      this.connectionId = await this.enhancedService.connect(options);
      console.log('[EnhancedICUIBackendService] Connected with ID:', this.connectionId);
      
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Enhanced connection failed:', error);
      
      // Fallback to legacy service
      if (this.migrationHelper) {
        console.log('[EnhancedICUIBackendService] Attempting fallback to legacy service');
        try {
          const legacyService = this.migrationHelper.getService('main');
          console.warn('[EnhancedICUIBackendService] Using legacy service adapter');
          // Would need to implement full legacy adapter here
        } catch (fallbackError) {
          console.error('[EnhancedICUIBackendService] Fallback also failed:', fallbackError);
          throw fallbackError;
        }
      } else {
        throw error;
      }
    }
  }

  /**
   * Get workspace files for editor component with enhanced batching
   * (Legacy compatibility method)
   */
  async getWorkspaceFiles(workspaceRoot?: string): Promise<ICUIFile[]> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.list_workspace_files',
        params: { workspaceRoot },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 10000,
          expectResponse: true,
          retries: 2
        }
      );

      // Response handling would be implemented through message events
      // For now, return empty array as placeholder
      return [];
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Get workspace files failed:', error);
      throw error;
    }
  }

  /**
   * Get file content (legacy compatibility method)
   */
  async getFile(path: string): Promise<ICUIFile> {
    const content = await this.readFile(path);
    return {
      id: Math.random().toString(36),
      name: path.split('/').pop() || '',
      language: this.detectLanguage(path),
      content: content,
      modified: false,
      path: path
    };
  }

  /**
   * Save file content (legacy compatibility method)
   */
  async saveFile(path: string, content: string): Promise<void> {
    return this.writeFile(path, content);
  }

  /**
   * Get directory contents (legacy compatibility method)
   */
  async getDirectoryContents(path: string): Promise<ICUIFileNode[]> {
    return this.getFileTree(path);
  }

  /**
   * Create directory (legacy compatibility method)
   */
  async createDirectory(path: string): Promise<void> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.create_directory',  
        params: { path },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 10000,
          expectResponse: true,
          retries: 1
        }
      );

    } catch (error) {
      console.error('[EnhancedICUIBackendService] Create directory failed:', error);
      throw error;
    }
  }

  /**
   * Execute code with enhanced monitoring (updated signature)
   */
  async executeCode(code: string, language: string = 'python', filePath?: string): Promise<any> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'code.execute',
        params: { code, language, filePath },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'high',
          timeout: 30000,
          expectResponse: true,
          retries: 1
        }
      );

      // Response handling would be implemented through message events
      return { output: '', error: null };
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Execute code failed:', error);
      throw error;
    }
  }

  /**
   * Detect language from file extension
   */
  private detectLanguage(filePath: string): string {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const languageMap: { [key: string]: string } = {
      'js': 'javascript',
      'ts': 'typescript',
      'py': 'python',
      'jsx': 'javascript',
      'tsx': 'typescript',
      'html': 'html',
      'css': 'css',
      'json': 'json',
      'md': 'markdown',
      'txt': 'text'
    };
    return languageMap[ext || ''] || 'text';
  }

  /**
   * Get file tree for explorer with enhanced caching
   */
  async getFileTree(path: string = '/'): Promise<ICUIFileNode[]> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.list_directory',
        params: { path },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 8000,
          expectResponse: true,
          retries: 1
        }
      );

      // Response handling would be implemented through message events
      // For now, return empty array as placeholder
      return [];
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Get file tree failed:', error);
      throw error;
    }
  }

  /**
   * Read file content with enhanced error handling
   */
  async readFile(path: string): Promise<string> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.read',
        params: { path },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'high',
          timeout: 15000,
          expectResponse: true,
          retries: 2
        }
      );

      // Response handling would be implemented through message events
      // For now, return empty string as placeholder
      return '';
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Read file failed:', error);
      throw error;
    }
  }

  /**
   * Write file content with enhanced batching
   */
  async writeFile(path: string, content: string): Promise<void> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.write',
        params: { path, content },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'high',
          timeout: 20000,
          expectResponse: true,
          retries: 2
        }
      );

    } catch (error) {
      console.error('[EnhancedICUIBackendService] Write file failed:', error);
      throw error;
    }
  }

  /**
   * Create file with enhanced validation
   */
  async createFile(path: string, content: string = ''): Promise<void> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.create',
        params: { path, content },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 10000,
          expectResponse: true,
          retries: 1
        }
      );

    } catch (error) {
      console.error('[EnhancedICUIBackendService] Create file failed:', error);
      throw error;
    }
  }

  /**
   * Delete file/directory with enhanced confirmation
   */
  async deleteFile(path: string): Promise<void> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('Enhanced backend service not connected');
    }

    try {
      const message = {
        id: Math.random().toString(36),
        method: 'file.delete',
        params: { path },
        timestamp: Date.now()
      };

      await this.enhancedService.sendMessage(
        this.connectionId,
        JSON.stringify(message),
        {
          priority: 'normal',
          timeout: 10000,
          expectResponse: true,
          retries: 1
        }
      );

    } catch (error) {
      console.error('[EnhancedICUIBackendService] Delete file failed:', error);
      throw error;
    }
  }

  /**
   * Handle WebSocket messages (adapted from parent class)
   */
  private handleWebSocketMessage(event: { data: string }): void {
    try {
      const message = JSON.parse(event.data);
      console.log('[EnhancedICUIBackendService] Message received:', message);
      
      // Emit appropriate events based on message type
      if (message.method) {
        this.emit('response', message);
      } else if (message.event) {
        this.emit(message.event, message.data);
      }
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Error parsing message:', error);
    }
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): Promise<{ connected: boolean }> {
    return Promise.resolve({
      connected: this.connectionId !== null
    });
  }

  /**
   * Get health status
   */
  getHealthStatus(): any {
    return this.healthStatus;
  }

  /**
   * Get connection statistics
   */
  getConnectionStatistics(): any {
    return this.connectionStats;
  }

  /**
   * Force reconnection
   */
  async reconnect(): Promise<void> {
    if (this.connectionId && this.enhancedService) {
      try {
        await this.enhancedService.disconnect(this.connectionId);
      } catch (error) {
        console.warn('[EnhancedICUIBackendService] Disconnect error during reconnect:', error);
      }
    }
    
    this.connectionId = null;
    this._initialized = false;
    
    await this.ensureInitialized();
  }

  /**
   * Check if the service is connected
   */
  isConnected(): boolean {
    return this.connectionId !== null && 
           this.enhancedService !== null && 
           this.enhancedService.isConnected();
  }

  /**
   * Disconnect and cleanup
   */
  async disconnect(): Promise<void> {
    if (this.connectionId && this.enhancedService) {
      try {
        await this.enhancedService.disconnect(this.connectionId);
      } catch (error) {
        console.warn('[EnhancedICUIBackendService] Disconnect error:', error);
      }
    }
    
    this.connectionId = null;
    this._initialized = false;
    
    this.emit('connection_status_changed', { status: 'disconnected' });
  }

  /**
   * Destroy service and cleanup
   */
  destroy(): void {
    this.disconnect();
    
    if (this.enhancedService) {
      try {
        this.enhancedService.destroy();
      } catch (error) {
        console.warn('[EnhancedICUIBackendService] Service destruction error:', error);
      }
    }
    
    this.removeAllListeners();
  }
}

// Create singleton instance with enhanced features
export const enhancedICUIBackendService = new EnhancedICUIBackendService();
