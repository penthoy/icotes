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
  private _initializing = false;
  private _initAttempts = 0;
  
  // Backend configuration
  private baseUrl: string = '';
  private websocketUrl: string = '';
  
  // Health monitoring
  private healthStatus: any = null;
  private connectionStats: any = null;
  // Hop (SSH) context
  private hopSession: any = null;
  private hopSessionsCache: any[] = [];
  
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
    
    // Initialize URLs dynamically but don't auto-connect
    // Connection will happen when ensureInitialized() is called
    this.initializeUrls().then(() => {
      // URLs are ready, but don't auto-initialize service yet
      // This prevents race conditions with ensureInitialized()
    }).catch(error => {
      console.warn('ICUIBackendService: Failed to initialize URLs in constructor:', error);
    });
  }

  /**
   * Initialize URLs using dynamic configuration
   */
  private async initializeUrls(): Promise<void> {
    // Guard against multiple simultaneous calls
    if (this.baseUrl && this.websocketUrl) {
      return; // Already resolved
    }
    
    try {
      const dynamicConfig = await configService.getConfig();
      this.baseUrl = dynamicConfig.base_url;  // Use base_url, not api_url
      this.websocketUrl = dynamicConfig.ws_url;
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('🔧 ICUIBackendService using dynamic URLs:', {
          baseUrl: this.baseUrl,
          websocketUrl: this.websocketUrl
        });
      }
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
      
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('🔄 ICUIBackendService using fallback URLs:', {
          baseUrl: this.baseUrl,
          websocketUrl: this.websocketUrl
        });
      }
    }
  }

  /**
   * Initialize enhanced WebSocket service
   */
  private initializeEnhancedService(): void {
    // Only initialize if URLs are available and service not already created
    if (!this.baseUrl || !this.websocketUrl) {
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('🔄 ICUIBackendService URLs not ready, delaying initialization');
      }
      return;
    }
    
    if (this.enhancedService) {
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('🔄 ICUIBackendService enhanced service already initialized');
      }
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

    // Service initialized - connection will be established when needed

    // Set up migration helper (disabled to prevent duplicate service initialization)
    this.migrationHelper = new WebSocketMigrationHelper({
      enableEnhancedService: false, // We already have our instance
      migrateMain: false,
      fallbackToLegacy: true,
      testMode: false
    });

    // Enhanced service event handlers
    this.enhancedService.on('connection_opened', (data: any) => {
      log.info('ICUIBackendService', 'Service connected', data);
      // Race fix: during first connect this.connectionId may not yet be assigned.
      if (!this.connectionId) {
        // Adopt the first opened connection while initializing.
        this.connectionId = data.connectionId;
      }
      if (data.connectionId === this.connectionId) {
        if (!this._initialized) {
          this._initialized = true;
          this.emit('connection_status_changed', { status: 'connected' });
        }
      } else {
        if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
          console.debug('[ICUIBackendService][event:connection_opened] ignoring foreign connection', {
            eventId: data.connectionId, current: this.connectionId
          });
        }
      }
    });

    this.enhancedService.on('connection_closed', (data: any) => {
      log.info('ICUIBackendService', 'Service disconnected', data);
      // Fix: Only handle disconnect if this is OUR connection
      if (data.connectionId === this.connectionId) {
        this._initialized = false;
        this.connectionId = null;
        this.emit('connection_status_changed', { status: 'disconnected' });
      }
    });

    // Also listen for the legacy events for compatibility
    this.enhancedService.on('connected', (data: any) => {
      // console.log('[ICUIBackendService] Enhanced service connected (legacy event):', data);
      // Fix: Only set initialized if this is OUR connection (or no connectionId specified, legacy fallback)
      if (!this.connectionId && data.connectionId) {
        this.connectionId = data.connectionId; // adopt if missing (race window)
      }
      if (!data.connectionId || data.connectionId === this.connectionId) {
        if (!this._initialized) {
          this._initialized = true;
          this.emit('connection_status_changed', { status: 'connected' });
        }
      } else if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.debug('[ICUIBackendService][event:connected] ignored foreign connection', {
          eventId: data.connectionId, current: this.connectionId
        });
      }
    });

    this.enhancedService.on('disconnected', (data: any) => {
      // console.log('[ICUIBackendService] Enhanced service disconnected (legacy event):', data);
      // Fix: Only handle disconnect if this is OUR connection (or no connectionId specified, legacy fallback)
      if (!data.connectionId || data.connectionId === this.connectionId) {
        this._initialized = false;
        this.connectionId = null;
        this.emit('connection_status_changed', { status: 'disconnected' });
      }
    });

    this.enhancedService.on('message', (data: any) => {
      if (data.connectionId === this.connectionId) {
  log.debug('ICUIBackendService', '[BE] message passthrough', { connectionId: data.connectionId });
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
        // Note: connection_closed already handles cleanup, this is just for logging
      }
    });
  }

  /**
   * Ensure service is initialized before operations
   */
  private async ensureInitialized(): Promise<void> {
    if (this._initialized || this._initializing) {
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.debug('[ICUIBackendService][ensureInitialized] early-exit', {
          initialized: this._initialized,
          initializing: this._initializing,
          connectionId: this.connectionId
        });
      }
      return;
    }
    // New guard: if we already have a live connection but _initialized never flipped (race), repair state
    if (this.connectionId && this.enhancedService) {
      try {
        const statusObj: any = (this.enhancedService as any).getConnectionStatus?.(this.connectionId);
        if (statusObj?.status === 'connected') {
          this._initialized = true;
          this.emit('connection_status_changed', { status: 'connected', repaired: true });
          if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
            console.debug('[ICUIBackendService][ensureInitialized] repaired-missing-initialized-flag', { connectionId: this.connectionId });
          }
          return;
        }
      } catch {/* ignore */}
    }
    this._initializing = true;
    const attempt = ++this._initAttempts;
    log.info('ICUIBackendService', 'Auto-initializing service', { attempt });
    try {
      // Add timeout to prevent blocking indefinitely
      const initPromise = this.performInitialization();
      const timeoutPromise = new Promise<void>((_, reject) => {
        setTimeout(() => reject(new Error('Initialization timeout')), 15000); // 15s timeout
      });
      
      await Promise.race([initPromise, timeoutPromise]);
    } catch (error) {
      console.warn('[ICUIBackendService] Initialization failed:', error);
      // Don't throw - allow the service to continue working with degraded functionality
    } finally {
      this._initializing = false;
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.debug('[ICUIBackendService][ensureInitialized] complete', {
          initialized: this._initialized,
          connectionId: this.connectionId
        });
      }
    }
  }

  private async performInitialization(): Promise<void> {
    if (!this.baseUrl || !this.websocketUrl) {
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.debug('[ICUIBackendService][ensureInitialized] resolving URLs');
      }
      await this.initializeUrls();
    }
    if (!this.enhancedService) {
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.debug('[ICUIBackendService][ensureInitialized] creating enhanced service');
      }
      this.initializeEnhancedService();
    }
    if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
      console.debug('[ICUIBackendService][ensureInitialized] calling initializeConnection');
    }
    await this.initializeConnection();
    // Note: _initialized is set by connection event handlers, not here
    // This prevents race condition where we think we're initialized before connection is actually open
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
      // Post-connect safety: If event handlers missed initial open events (race), mark initialized now.
      if (!this._initialized) {
        if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
          console.debug('[ICUIBackendService][initializeConnection] post-connect initializing fallback');
        }
        this._initialized = true;
        this.emit('connection_status_changed', { status: 'connected' });
      }
      
      // Verify connection is actually established
      const connStatus = (this.enhancedService as any).getConnectionStatus?.(this.connectionId);
      if (connStatus?.status !== 'connected') {
        console.warn('[ICUIBackendService] Connection ID received but status not yet connected, will wait for events');
      }
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        let stats: any = undefined;
        try {
          const maybeFn = (this.enhancedService as any)?.getStatistics;
          if (typeof maybeFn === 'function') {
            stats = maybeFn.call(this.enhancedService);
          }
        } catch { /* ignore */ }
        console.debug('[ICUIBackendService][initializeConnection] post-connect snapshot', {
          connectionId: this.connectionId,
            status: connStatus?.status,
            hasStats: !!stats
        });
      }
      
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
      // Use REST API for directory creation via /api/files with type: 'directory'
      const url = `${this.baseUrl}/api/files`;
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Creating directory at:', url, 'path:', path);
      }
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, type: 'directory', create_dirs: true }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create directory: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Directory create response:', result);
      }
      
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
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Fetching directory contents from:', url);
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch directory contents: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Directory contents response:', result);
      }
      
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
      
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Returning sorted nodes:', sortedNodes.length);
      }
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
   * Move or rename files/directories using REST API endpoint.
   */
  async moveFile(sourcePath: string, destinationPath: string, overwrite = false): Promise<void> {
    await this.ensureInitialized();

    try {
      const url = `${this.baseUrl}/api/files/move`;
      console.log('[EnhancedICUIBackendService] Moving file:', { sourcePath, destinationPath, overwrite });

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ source_path: sourcePath, destination_path: destinationPath, overwrite }),
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail?.detail || `Failed to move file: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log('[EnhancedICUIBackendService] File move response:', result);

      if (!result.success) {
        throw new Error(result.message || 'Failed to move file');
      }
    } catch (error) {
      console.error('[EnhancedICUIBackendService] Move file failed:', error);
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
        log.debug('ICUIBackendService', '[BE] Filesystem event received', { event: message.event, data: message.data });
        // Emit a payload that matches listener expectations: event + data
        // Keep a descriptive type for compatibility and include a normalized path
        const filePath =
          message.data?.file_path ??
          message.data?.path ??
          message.data?.dir_path ??   // directory events
          message.data?.dest_path ??
          message.data?.src_path;
        log.debug('ICUIBackendService', '[BE] Emitting filesystem_event', { event: message.event, path: filePath });
        this.emit('filesystem_event', {
          type: 'filesystem_event',
          event: message.event,
          path: filePath,
          data: message.data
        });
      } else if (message.type === 'hop_event') {
        // Unified hop events coming from backend websocket_api
        // Example: { type: 'hop_event', event: 'hop.status', data: { ...session } }
        try {
          if (message.event === 'hop.status') {
            this.hopSession = this.normalizeHopSession(message.data);
            this.emit('hop_status', this.hopSession);
          }
          if (message.event === 'hop.sessions' && message.data?.sessions) {
            this.hopSessionsCache = message.data.sessions;
          }
          this.emit('hop_event', { event: message.event, data: message.data });
        } catch (e) {
          console.warn('[ICUIBackendService] Failed to process hop_event:', e);
        }
      } else if (message.type === 'subscribed') {
        log.info('ICUIBackendService', '[BE] Subscription confirmed', { topics: message.topics });
        // Reduced debug: console.log('[ICUIBackendService] Subscription confirmed:', message.topics);
      } else if (message.type === 'unsubscribed') {
        log.info('ICUIBackendService', '[BE] Unsubscription confirmed', { topics: message.topics });
        // Reduced debug: console.log('[ICUIBackendService] Unsubscription confirmed:', message.topics);
      } else if (message.type === 'welcome') {
        log.info('ICUIBackendService', '[BE] Welcome message received', { connectionId: message.connection_id });
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

  // ==================== Hop (SSH) API ====================
  /**
   * Get current hop session status (local vs remote).
   * Also updates cached hopSession and emits 'hop_status'.
   */
  async getHopStatus(): Promise<any> {
    await this.ensureInitialized();
    try {
      const url = `${this.baseUrl}/api/hop/status`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const session = await resp.json();
  this.hopSession = this.normalizeHopSession(session);
      this.emit('hop_status', this.hopSession);
      return session;
    } catch (e) {
      console.warn('[ICUIBackendService] getHopStatus failed:', e);
      return this.hopSession;
    }
  }

  /** List saved SSH credentials */
  async listHopCredentials(): Promise<any[]> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/credentials`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  /** Create SSH credential */
  async createHopCredential(cred: {
    name: string; host: string; port?: number; username?: string; auth?: 'password'|'privateKey'|'agent'; privateKeyId?: string; defaultPath?: string;
  }): Promise<any> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/credentials`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cred)
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    this.emit('hop_credentials_updated');
    return data;
  }

  /** Update SSH credential */
  async updateHopCredential(id: string, updates: Partial<{ name: string; host: string; port: number; username: string; auth: 'password'|'privateKey'|'agent'; privateKeyId: string; defaultPath: string; }>): Promise<any> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/credentials/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    this.emit('hop_credentials_updated');
    return data;
  }

  /** Delete SSH credential */
  async deleteHopCredential(id: string): Promise<void> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/credentials/${encodeURIComponent(id)}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    this.emit('hop_credentials_updated');
  }

  /** Upload private key, returns keyId */
  async uploadHopKey(file: File): Promise<string> {
    await this.ensureInitialized();
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${this.baseUrl}/api/hop/keys`, { method: 'POST', body: form });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    return data.keyId as string;
  }

  /** Connect using a credential */
  async connectHop(credentialId: string, opts?: { password?: string; passphrase?: string }): Promise<any> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credentialId, password: opts?.password, passphrase: opts?.passphrase })
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const session = await resp.json();
    this.hopSession = this.normalizeHopSession(session);
    this.emit('hop_status', this.hopSession);
    return session;
  }

  /** Disconnect current hop or a specific context */
  async disconnectHop(contextId?: string): Promise<any> {
    await this.ensureInitialized();
    const body = contextId ? JSON.stringify({ context_id: contextId }) : undefined;
    const resp = await fetch(`${this.baseUrl}/api/hop/disconnect`, { 
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const session = await resp.json();
    this.hopSession = this.normalizeHopSession(session);
    this.emit('hop_status', this.hopSession);
    return session;
  }

  /** List all active hop sessions */
  async listHopSessions(): Promise<any[]> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/sessions`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (Array.isArray(data.sessions)) {
      this.hopSessionsCache = data.sessions;
    }
    return this.hopSessionsCache;
  }

  /** Return cached hop sessions (populated via events or explicit listHopSessions). */
  listHopSessionsCached(): any[] { return this.hopSessionsCache; }

  /** Hop to a different context */
  async hopTo(contextId: string): Promise<any> {
    await this.ensureInitialized();
    const resp = await fetch(`${this.baseUrl}/api/hop/hop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contextId }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const session = await resp.json();
    this.hopSession = this.normalizeHopSession(session);
    this.emit('hop_status', this.hopSession);
    return session;
  }

  /** Send (copy) a set of files/folders from current (or specified) context to target context default path */
  async sendFilesToContext(targetContextId: string, paths: string[], opts?: { sourceContextId?: string; commonPrefix?: string }): Promise<any> {
    await this.ensureInitialized();
    if (!paths || paths.length === 0) return { success: true, created: [] };
    const payload: any = {
      target_context_id: targetContextId,
      paths,
    };
    if (opts?.sourceContextId) payload.source_context_id = opts.sourceContextId;
    if (opts?.commonPrefix) payload.common_prefix = opts.commonPrefix;
    log.info('BackendService', 'sendFilesToContext request', { targetContextId, count: paths.length, payload });
    const resp = await fetch(`${this.baseUrl}/api/hop/send-files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const detail = await resp.json().catch(() => ({}));
      log.error('BackendService', 'sendFilesToContext failed', { status: resp.status, detail });
      throw new Error(detail?.detail || `Failed to send files: HTTP ${resp.status}`);
    }
    const data = await resp.json();
    log.info('BackendService', 'sendFilesToContext response', { created: data?.created?.length, errors: data?.errors?.length });
    return data;
  }

  private normalizeHopSession(raw: any) {
    if (!raw || typeof raw !== 'object') return raw;
    const status = raw.status || (raw.connected ? 'connected' : 'disconnected');
    const connected = status === 'connected';
    // Map common aliases
    return {
      ...raw,
      status,
      connected,
      credential_id: raw.credentialId ?? raw.credential_id,
      context_id: raw.contextId ?? raw.context_id,
    };
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

    log.debug('EnhancedICUIBackendService', '[BE] Sending notification', { method, params });
    if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
      console.log('[EnhancedICUIBackendService] Sending notification:', { method, params, message, connectionId: this.connectionId });
    }

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
      if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
        console.log('[EnhancedICUIBackendService] Notification response:', response);
      }
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
    // First check if we're already connected without waiting for full initialization
    // This makes the connection status responsive
    let connected = false;
    
    if (this.connectionId && this.enhancedService) {
      try {
        // Check connection status immediately without waiting for ensureInitialized
        const statusObj: any = (this.enhancedService as any).getConnectionStatus
          ? (this.enhancedService as any).getConnectionStatus(this.connectionId)
          : null;
        if (statusObj && statusObj.status === 'connected') {
          connected = true;
        } else {
          // Fallback to aggregate service connectivity
          connected = this.enhancedService.isConnected();
        }
      } catch (err) {
        // Non-fatal; continue with initialization check
        if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
          console.warn('[ICUIBackendService] getConnectionStatus quick check failed', err);
        }
      }
    }
    
    // If not connected yet, try to initialize (but don't block the UI)
    if (!connected && !this._initializing) {
      // Start initialization in background but return current status immediately
      this.ensureInitialized().catch(err => {
        console.warn('[ICUIBackendService] Background initialization failed:', err);
      });
    }
    
    if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
      console.debug('[ICUIBackendService][getConnectionStatus] returning', {
        connected,
        connectionId: this.connectionId,
        initialized: this._initialized,
        initializing: this._initializing
      });
    }
    return { connected };
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
    if (!this.connectionId || !this.enhancedService) return false;
    try {
      const statusObj: any = (this.enhancedService as any).getConnectionStatus
        ? (this.enhancedService as any).getConnectionStatus(this.connectionId)
        : null;
      if (statusObj && statusObj.status === 'connected') return true;
    } catch {}
    const fallback = this.enhancedService.isConnected();
    if ((import.meta as any).env?.VITE_DEBUG_EXPLORER === 'true') {
      console.debug('[ICUIBackendService][isConnected] fallback result', {
        fallback,
        connectionId: this.connectionId
      });
    }
    return fallback;
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

  
  // ==================== SCM (Source Control) Methods ====================
  
  /**
   * Get Git repository information
   */
  async getScmRepoInfo(): Promise<any> {
    try {
      const url = `${this.baseUrl}/api/scm/repo`;
      console.log('[ICUIBackendService] Getting SCM repo info from:', url);
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to get repo info: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('[ICUIBackendService] Get SCM repo info failed:', error);
      throw error;
    }
  }

  /**
   * Get Git status (staged/unstaged/untracked files)
   */
  async getScmStatus(): Promise<any> {
    try {
      const url = `${this.baseUrl}/api/scm/status`;
      console.log('[ICUIBackendService] Getting SCM status from:', url);
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to get status: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('[ICUIBackendService] Get SCM status failed:', error);
      throw error;
    }
  }

  /**
   * Get Git diff for a file or entire working tree
   */
  async getScmDiff(path?: string): Promise<any> {
    try {
      const url = new URL(`${this.baseUrl}/api/scm/diff`);
      if (path) {
        url.searchParams.set('path', path);
      }
      
      console.log('[ICUIBackendService] Getting SCM diff from:', url.toString());
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to get diff: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('[ICUIBackendService] Get SCM diff failed:', error);
      throw error;
    }
  }

  /**
   * Stage files for commit
   */
  async scmStage(paths: string[]): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/stage`;
      console.log('[ICUIBackendService] Staging files:', paths);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to stage files: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM stage failed:', error);
      throw error;
    }
  }

  /**
   * Unstage files
   */
  async scmUnstage(paths: string[]): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/unstage`;
      console.log('[ICUIBackendService] Unstaging files:', paths);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to unstage files: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM unstage failed:', error);
      throw error;
    }
  }

  /**
   * Discard changes to files
   */
  async scmDiscard(paths: string[]): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/discard`;
      console.log('[ICUIBackendService] Discarding changes for files:', paths);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ paths }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to discard changes: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM discard failed:', error);
      throw error;
    }
  }

  /**
   * Commit staged changes
   */
  async scmCommit(message: string, amend: boolean = false, signoff: boolean = false): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/commit`;
      console.log('[ICUIBackendService] Committing with message:', message);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message, amend, signoff }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to commit: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM commit failed:', error);
      throw error;
    }
  }

  /**
   * Get Git branches
   */
  async getScmBranches(): Promise<any> {
    try {
      const url = `${this.baseUrl}/api/scm/branches`;
      console.log('[ICUIBackendService] Getting SCM branches from:', url);
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to get branches: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data;
    } catch (error) {
      console.error('[ICUIBackendService] Get SCM branches failed:', error);
      throw error;
    }
  }

  /**
   * Checkout a branch
   */
  async scmCheckout(branch: string, create: boolean = false): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/checkout`;
      console.log('[ICUIBackendService] Checking out branch:', branch, 'create:', create);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ branch, create }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to checkout branch: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM checkout failed:', error);
      throw error;
    }
  }

  /**
   * Pull from remote
   */
  async scmPull(): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/pull`;
      console.log('[ICUIBackendService] Pulling from remote');
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to pull: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM pull failed:', error);
      throw error;
    }
  }

  /**
   * Push to remote
   */
  async scmPush(setUpstream: boolean = false): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/push`;
      console.log('[ICUIBackendService] Pushing to remote, setUpstream:', setUpstream);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ set_upstream: setUpstream }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to push: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] SCM push failed:', error);
      throw error;
    }
  }

  /**
   * Initialize a Git repository
   */
  async initializeGitRepo(): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/api/scm/init`;
      console.log('[ICUIBackendService] Initializing Git repository');
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`Failed to initialize Git repository: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.data?.ok || false;
    } catch (error) {
      console.error('[ICUIBackendService] Git initialization failed:', error);
      throw error;
    }
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

// Create singleton instance (guarded for HMR to prevent duplicate connections)
const __GLOBAL_BACKEND_KEY__ = '__ICUI_BACKEND_SERVICE_SINGLETON__';
const __g: any = globalThis as any;
if (!__g[__GLOBAL_BACKEND_KEY__]) {
  __g[__GLOBAL_BACKEND_KEY__] = new ICUIBackendService();
}
export const icuiBackendService = __g[__GLOBAL_BACKEND_KEY__] as ICUIBackendService;

// Legacy compatibility export (alias)
export const enhancedICUIBackendService = icuiBackendService;
