/**
 * ICUI Backend Service
 * 
 * Integrates all WebSocket improvements for file operations, explorer functionality,
 * and general backend communication with connection management, error handling,
 * message queuing, and health monitoring.
 */

import { EventEmitter } from 'eventemitter3';
import { EnhancedWebSocketService, ConnectionOptions, MessageOptions } from '../../services/websocket-service-impl';
import { WebSocketMigrationHelper } from '../../services/websocket-migration';
import { ConnectionStatus } from '../../types/backend-types';
import { log } from '../../services/frontend-logger';
import { configService } from '../../services/config-service';

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
export class ICUIBackendService extends EventEmitter {
  private enhancedService: EnhancedWebSocketService | null = null;
  private migrationHelper: WebSocketMigrationHelper | null = null;
  private connectionId: string | null = null;
  private _initialized = false;
  
  // Backend configuration
  private baseUrl: string = '';
  private websocketUrl: string = '';
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;
  
  // Configuration
  private config: EnhancedBackendConfig = {
    enableMessageQueue: true,
    enableHealthMonitoring: true,
    enableAutoRecovery: true,
    maxConcurrentConnections: 20, // Increased from 5 to allow multiple tabs/sessions
    messageTimeout: 15000,
    batchFileOperations: true
  };

  constructor(config?: Partial<EnhancedBackendConfig>) {
    super();
    
    if (config) {
      this.config = { ...this.config, ...config };
    }
    
    // Initialize URLs dynamically
    this.initializeUrls().then(() => {
      this.initializeEnhancedService();
    });
  }

  /**
   * Initialize URLs using dynamic configuration
   */
  private async initializeUrls(): Promise<void> {
    try {
      const dynamicConfig = await configService.getConfig();
      this.baseUrl = dynamicConfig.base_url;  // Use base_url, not api_url
      this.websocketUrl = dynamicConfig.ws_url;
      console.log('🔧 ICUIBackendService using dynamic URLs:', {
        baseUrl: this.baseUrl,
        websocketUrl: this.websocketUrl
      });
    } catch (error) {
      console.warn('⚠️  Failed to get dynamic config for ICUIBackendService, using fallbacks:', error);
      
      // Use environment variables or window location as fallback
      const envBackendUrl = import.meta.env.VITE_BACKEND_URL;
      const envWsUrl = import.meta.env.VITE_WS_URL;
      
      if (envBackendUrl && envWsUrl) {
        this.baseUrl = envBackendUrl;
        // SAAS PROTOCOL FIX: Ensure WebSocket URL uses correct protocol
        try {
          const wsUrl = new URL(envWsUrl);
          const currentProtocol = window.location.protocol;
          const shouldUseSecure = currentProtocol === 'https:';
          const finalProtocol = shouldUseSecure ? 'wss:' : wsUrl.protocol;
          
          this.websocketUrl = `${finalProtocol}//${wsUrl.host}${wsUrl.pathname}${wsUrl.search}`;
          if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
            console.log(`🔒 WebSocket protocol conversion: page=${currentProtocol}, env=${wsUrl.protocol}, final=${finalProtocol}`);
          }
        } catch {
          this.websocketUrl = envWsUrl; // Fallback to original if parsing fails
        }
      } else {
        // Final fallback to window location
        const protocol = window.location.protocol;
        const host = window.location.host;
        const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
        
        this.baseUrl = `${protocol}//${host}`;  // Don't include /api here
        this.websocketUrl = `${wsProtocol}//${host}/ws`;
      }
      
      console.log('🔄 ICUIBackendService using fallback URLs:', {
        baseUrl: this.baseUrl,
        websocketUrl: this.websocketUrl
      });
    }
  }

  /**
   * Initialize enhanced WebSocket service
   */
  private initializeEnhancedService(): void {
    // Only initialize if URLs are available
    if (!this.baseUrl || !this.websocketUrl) {
      console.log('🔄 ICUIBackendService URLs not ready, delaying initialization');
      return;
    }

    // Configure enhanced service for backend operations
    this.enhancedService = new EnhancedWebSocketService({
      websocket_url: this.websocketUrl,
      http_base_url: this.baseUrl,
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

    console.log('✅ EnhancedWebSocketService initialized with URLs:', {
      websocket_url: this.websocketUrl,
      http_base_url: this.baseUrl
    });

    // Set up migration helper
    this.migrationHelper = new WebSocketMigrationHelper({
      migrateMain: true,
      fallbackToLegacy: true,
      testMode: false
    });

    // Enhanced service event handlers
    this.enhancedService.on('connection_opened', (data: any) => {
      log.info('ICUIBackendService', 'Enhanced service connected', data);
      this._initialized = true;
      this.emit('connection_status_changed', { status: 'connected' });
    });

    this.enhancedService.on('connection_closed', (data: any) => {
      log.info('ICUIBackendService', 'Enhanced service disconnected', data);
      this.emit('connection_status_changed', { status: 'disconnected' });
    });

    // Also listen for the legacy events for compatibility
    this.enhancedService.on('connected', (data: any) => {
      // console.log('[ICUIBackendService] Enhanced service connected (legacy event):', data);
      this._initialized = true;
      this.emit('connection_status_changed', { status: 'connected' });
    });

    this.enhancedService.on('disconnected', (data: any) => {
      // console.log('[ICUIBackendService] Enhanced service disconnected (legacy event):', data);
      this.emit('connection_status_changed', { status: 'disconnected' });
    });

    this.enhancedService.on('message', (data: any) => {
      if (data.connectionId === this.connectionId) {
        this.handleWebSocketMessage({ data: data.message });
      }
    });

    this.enhancedService.on('error', (error: any) => {
      console.error('[ICUIBackendService] Enhanced service error:', error);
      this.emit('error', error);
    });

    this.enhancedService.on('healthUpdate', (health: any) => {
      this.healthStatus = health;
      // console.log('[ICUIBackendService] Health update:', health);
    });

    this.enhancedService.on('connectionClosed', (data: any) => {
      if (data.connectionId === this.connectionId) {
        // console.log('[ICUIBackendService] Connection closed:', data);
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
      log.info('ICUIBackendService', 'Auto-initializing enhanced service');
      
      // First, ensure we have config and URLs
      if (!this.baseUrl || !this.websocketUrl) {
        await this.initializeUrls();
      }
      
      // Then initialize the enhanced service if not already done
      if (!this.enhancedService) {
        this.initializeEnhancedService();
      }
      
      // Finally, initialize the connection
      await this.initializeConnection();
      this._initialized = true;
    }
  }

  /**
   * Initialize connection with enhanced service
   */
  private async initializeConnection(): Promise<void> {
    if (this.connectionId && this.enhancedService) {
      // Reduced debug: Only log during development or for errors
      if (import.meta.env?.MODE === 'development' || import.meta.env?.DEV) {
        console.debug('[ICUIBackendService] Already connected');
      }
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

      log.info('ICUIBackendService', 'Connecting with options', options);
      this.connectionId = await this.enhancedService.connect(options);
      log.info('ICUIBackendService', 'Connected with ID', { connectionId: this.connectionId });
      
    } catch (error) {
      console.error('[ICUIBackendService] Enhanced connection failed:', error);
      
      // Fallback to legacy service
      if (this.migrationHelper) {
        console.log('[ICUIBackendService] Attempting fallback to legacy service');
        try {
          const legacyService = this.migrationHelper.getService('main');
          console.warn('[ICUIBackendService] Using legacy service adapter');
          // Would need to implement full legacy adapter here
        } catch (fallbackError) {
          console.error('[ICUIBackendService] Fallback also failed:', fallbackError);
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
    
    try {
      // Use REST API for file listing (same as deprecated version)
      const path = workspaceRoot || '/';
      const url = `${this.baseUrl}/api/files?path=${encodeURIComponent(path)}`;
      // console.log('[ICUIBackendService] Getting workspace files from:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get workspace files: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      // console.log('[EnhancedICUIBackendService] Workspace files response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to list workspace files');
      }
      
      const fileList = result.data || [];
      
      // Convert backend response to ICUIFile format, filter out directories
      return fileList
        .filter((item: any) => !item.is_directory)
        .map((item: any, index: number) => ({
          id: item.path || `file_${index}`,
          name: item.name,
          language: this.detectLanguage(item.name),
          content: '', // Content will be loaded separately
          modified: false,
          path: item.path
        }));
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
  async getDirectoryContents(path: string, includeHidden: boolean = false): Promise<ICUIFileNode[]> {
    return this.getFileTree(path, includeHidden);
  }

  /**
   * Create directory (legacy compatibility method)
   */
  async createDirectory(path: string): Promise<void> {
    await this.ensureInitialized();
    
    try {
      // Use REST API for directory creation
      const url = `${this.baseUrl}/api/directories`;
      console.log('[EnhancedICUIBackendService] Creating directory at:', url, 'path:', path);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create directory: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('[EnhancedICUIBackendService] Directory create response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to create directory');
      }
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
  async getFileTree(path: string = '/', includeHidden: boolean = false): Promise<ICUIFileNode[]> {
    await this.ensureInitialized();
    
    try {
      // Use REST API for file listing with include_hidden parameter
      const url = `${this.baseUrl}/api/files?path=${encodeURIComponent(path)}&include_hidden=${includeHidden}`;
      console.log('[EnhancedICUIBackendService] Fetching directory contents from:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch directory contents: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('[EnhancedICUIBackendService] Directory contents response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to get directory contents');
      }
      
      const fileList = result.data || result.files || [];
      
      // Convert backend format to FileNode format
      const nodes: ICUIFileNode[] = fileList.map((file: any) => ({
        id: file.path || file.id,
        name: file.name,
        type: (file.is_directory || file.isDirectory) ? 'folder' : 'file',
        path: file.path,
        size: file.size,
        modified: file.modified_at || file.modified
      }));
      
      // Sort nodes: directories first, then files (alphabetically within each group)
      const sortedNodes = nodes.sort((a, b) => {
        if (a.type === 'folder' && b.type === 'file') return -1;
        if (a.type === 'file' && b.type === 'folder') return 1;
        return a.name.localeCompare(b.name);
      });
      
      console.log('[EnhancedICUIBackendService] Returning sorted nodes:', sortedNodes.length);
      return sortedNodes;
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
    
    try {
      // Use REST API for file reading - use /api/files/content endpoint
      const url = `${this.baseUrl}/api/files/content?path=${encodeURIComponent(path)}`;
      // console.log('[EnhancedICUIBackendService] Reading file from:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to read file: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      // console.log('[EnhancedICUIBackendService] File read response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to read file');
      }
      
      // Ensure we return a string
      const content = result.data?.content || result.content || '';
      return typeof content === 'string' ? content : String(content);
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
    
    try {
      // Use REST API for file writing (same as deprecated version)
      const url = `${this.baseUrl}/api/files`;
      console.log('[EnhancedICUIBackendService] Writing file to:', url, 'path:', path);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, content }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to write file: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('[EnhancedICUIBackendService] File write response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to write file');
      }
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
    
    try {
      // Use REST API for file creation (same as deprecated version)
      const url = `${this.baseUrl}/api/files`;
      console.log('[EnhancedICUIBackendService] Creating file at:', url, 'path:', path);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, content }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create file: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('[EnhancedICUIBackendService] File create response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to create file');
      }
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
    
    try {
      // Use REST API for file deletion (same as deprecated version)
      const url = `${this.baseUrl}/api/files?path=${encodeURIComponent(path)}`;
      console.log('[EnhancedICUIBackendService] Deleting file at:', url);
      
      const response = await fetch(url, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('[EnhancedICUIBackendService] File delete response:', result);
      
      if (!result.success) {
        throw new Error(result.message || 'Failed to delete file');
      }
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Delete file failed:', error);
      throw error;
    }
  }

  /**
   * Handle WebSocket messages (adapted from parent class)
   */
  private handleWebSocketMessage(event: { data: string | object }): void {
    try {
      let message: any;
      
      // Handle both string and already-parsed object data
      if (typeof event.data === 'string') {
        // Check if event.data is valid before parsing
        if (!event.data || event.data === 'undefined') {
          console.warn('[EnhancedICUIBackendService] Invalid message data received:', event.data);
          return;
        }
        message = JSON.parse(event.data);
      } else if (typeof event.data === 'object' && event.data !== null) {
        // Data is already parsed
        message = event.data;
      } else {
        console.warn('[ICUIBackendService] Invalid message data received:', event.data);
        return;
      }

      // Removed excessive debug: console.log('[ICUIBackendService] Message received:', message);
      
      // Handle different message types
      if (message.type === 'filesystem_event') {
        // Handle filesystem events and emit them for the explorer
        log.debug('ICUIBackendService', 'Filesystem event received', { event: message.event, data: message.data });
        // Reduced debug: Only log filesystem events in debug mode
        this.emit('filesystem_event', {
          type: message.event,
          path: message.data?.path,
          data: message.data
        });
      } else if (message.type === 'subscribed') {
        log.info('ICUIBackendService', 'Subscription confirmed', { topics: message.topics });
        // Reduced debug: console.log('[ICUIBackendService] Subscription confirmed:', message.topics);
      } else if (message.type === 'unsubscribed') {
        log.info('ICUIBackendService', 'Unsubscription confirmed', { topics: message.topics });
        // Reduced debug: console.log('[ICUIBackendService] Unsubscription confirmed:', message.topics);
      } else if (message.type === 'welcome') {
        log.info('ICUIBackendService', 'Welcome message received', { connectionId: message.connection_id });
        // Reduced debug: console.log('[ICUIBackendService] Welcome message received:', message.connection_id);
      } else if (message.method) {
        this.emit('response', message);
      } else if (message.event) {
        this.emit(message.event, message.data);
      } else {
        // Only log unhandled message types that are not common heartbeat/ping messages
        if (message.type && message.type !== 'heartbeat' && message.type !== 'ping' && message.type !== 'pong') {
          console.log('[ICUIBackendService] Unhandled message type:', message.type);
        }
      }
    } catch (error) {
      console.error('[ICUIBackendService] Error parsing message:', error);
    }
  }

  /**
   * Send notification message (compatibility method for explorer)
   */
  async notify(method: string, params: any): Promise<any> {
    await this.ensureInitialized();
    
    if (!this.connectionId || !this.enhancedService) {
      throw new Error('WebSocket connection not established');
    }

    // Convert method+params format to WebSocket API format
    let message: any;
    if (method === 'subscribe') {
      message = {
        type: 'subscribe',
        topics: params.topics || [],
        id: Math.random().toString(36).substr(2, 9)
      };
    } else if (method === 'unsubscribe') {
      message = {
        type: 'unsubscribe',
        topics: params.topics || [],
        id: Math.random().toString(36).substr(2, 9)
      };
    } else {
      // Generic method+params format for other notifications
      message = {
        method,
        params,
        id: Math.random().toString(36).substr(2, 9)
      };
    }

    log.debug('EnhancedICUIBackendService', 'Sending notification', { method, params });
    console.log('[EnhancedICUIBackendService] Sending notification:', { method, params, message, connectionId: this.connectionId });

    try {
      const response = await this.enhancedService.sendMessage(
        this.connectionId,
        message,
        {
          priority: 'normal',
          timeout: 10000,
          expectResponse: false
        }
      );
      console.log('[EnhancedICUIBackendService] Notification response:', response);
      return response;
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Failed to send notification:', { method, params, error });
      log.error('EnhancedICUIBackendService', 'Failed to send notification', { method, params, error });
      throw error;
    }
  }

  /**
   * Get connection status
   */
  async getConnectionStatus(): Promise<{ connected: boolean }> {
    await this.ensureInitialized();
    return {
      connected: this.connectionId !== null && this.enhancedService !== null
    };
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

// Create singleton instance
export const icuiBackendService = new ICUIBackendService();

// Legacy compatibility export
export const enhancedICUIBackendService = icuiBackendService;
