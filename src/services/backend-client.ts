/**
 * Backend HTTP Client for ICUI-ICPY Integration
 * 
 * This client provides a comprehensive HTTP interface for communicating with
 * the ICPY backend REST API. It includes request/response handling, error
 * management, authentication, and integration with the WebSocket service.
 */

import {
  WorkspaceState,
  WorkspaceFile,
  WorkspacePanel,
  WorkspaceTerminal,
  WorkspaceLayout,
  WorkspacePreferences,
  FileInfo,
  DirectoryTree,
  FileSearchResult,
  TerminalSession,
  TerminalConfig,
  CodeExecutionRequest,
  CodeExecutionResult,
  ApiResponse,
  ApiError,
  BackendConfig
} from '../types/backend-types';

export class BackendClient {
  private baseUrl: string;
  private requestTimeout: number;
  private authToken: string | null = null;

  constructor(private config: BackendConfig) {
    this.baseUrl = config.http_base_url;
    this.requestTimeout = config.request_timeout;
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string): void {
    this.authToken = token;
  }

  /**
   * Clear authentication token
   */
  clearAuthToken(): void {
    this.authToken = null;
  }

  /**
   * Make HTTP request with error handling
   */
  private async makeRequest<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {})
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    const requestOptions: RequestInit = {
      ...options,
      headers,
      signal: AbortSignal.timeout(this.requestTimeout)
    };

    try {
      const response = await fetch(url, requestOptions);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`HTTP ${response.status}: ${errorData.message || response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        console.error(`HTTP request failed: ${error.message}`);
        throw error;
      }
      throw new Error('Unknown HTTP request error');
    }
  }

  /**
   * Get server health status
   */
  async getHealth(): Promise<{ status: string; timestamp: string }> {
    return this.makeRequest('/health');
  }

  /**
   * Get server statistics
   */
  async getStatistics(): Promise<Record<string, any>> {
    return this.makeRequest('/api/statistics');
  }

  // Workspace Operations

  /**
   * Get workspace state
   */
  async getWorkspaceState(): Promise<WorkspaceState> {
    return {
      id: 'default',
      name: 'Default Workspace',
      description: 'Default workspace',
      created_at: new Date().toISOString(),
      last_accessed: new Date().toISOString(),
      files: [],
      panels: [],
      terminals: [],
      layout: {
        id: 'default',
        name: 'Default Layout',
        panels: [],
        created_at: new Date().toISOString(),
        is_default: true
      },
      preferences: {
        theme: 'dark',
        font_size: 14,
        font_family: 'monospace',
        tab_size: 2,
        word_wrap: false,
        line_numbers: true,
        auto_save: true,
        auto_save_delay: 10,
      },
      statistics: {
        files_count: 0,
        terminals_count: 0,
        panels_count: 0,
        total_characters: 0,
        total_lines: 0,
        last_updated: new Date().toISOString()
      }
    };
  }

  /**
   * Create new workspace
   */
  async createWorkspace(name: string, description?: string): Promise<WorkspaceState> {
    return this.makeRequest('/api/workspaces', {
      method: 'POST',
      body: JSON.stringify({ name, description })
    });
  }

  /**
   * Update workspace
   */
  async updateWorkspace(updates: Partial<WorkspaceState>): Promise<WorkspaceState> {
    return this.makeRequest(`/api/workspaces/${updates.id}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  /**
   * Delete workspace
   */
  async deleteWorkspace(): Promise<void> {
    return this.makeRequest('/api/workspaces/default', {
      method: 'DELETE'
    });
  }

  /**
   * Get workspace preferences
   */
  async getPreferences(): Promise<WorkspacePreferences> {
    return {
      theme: 'dark',
      font_size: 14,
      font_family: 'monospace',
      tab_size: 2,
      word_wrap: false,
      line_numbers: true,
      auto_save: true,
      auto_save_delay: 10
    };
  }

  /**
   * Update workspace preferences
   */
  async updatePreferences(preferences: Partial<WorkspacePreferences>): Promise<WorkspacePreferences> {
    return { ...this.getPreferences(), ...preferences };
  }

  /**
   * Get workspace statistics
   */
  async getWorkspaceStatistics(): Promise<Record<string, any>> {
    return {
      files_count: 0,
      terminals_count: 0,
      last_activity: new Date().toISOString()
    };
  }

  // File Operations

  /**
   * Get file by ID
   */
  async getFile(fileId: string): Promise<WorkspaceFile> {
    return this.makeRequest(`/api/files/${fileId}`);
  }

  /**
   * Create new file
   */
  async createFile(path: string, content: string = '', language?: string): Promise<WorkspaceFile> {
    return this.makeRequest('/api/files', {
      method: 'POST',
      body: JSON.stringify({
        path, 
        content, 
        encoding: 'utf-8',
        create_dirs: true
      })
    });
  }

  /**
   * Update file content
   */
  async updateFile(fileId: string, content: string): Promise<WorkspaceFile> {
    return this.makeRequest(`/api/files/${fileId}`, {
      method: 'PUT',
      body: JSON.stringify({ content })
    });
  }

  /**
   * Delete file
   */
  async deleteFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/files/${fileId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Get all files
   */
  async getFiles(): Promise<WorkspaceFile[]> {
    return this.makeRequest('/api/files');
  }

  /**
   * Set active file
   */
  async setActiveFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/files/${fileId}/activate`, {
      method: 'POST'
    });
  }

  /**
   * Save file
   */
  async saveFile(fileId: string, content: string): Promise<WorkspaceFile> {
    return this.updateFile(fileId, content);
  }

  /**
   * Close file
   */
  async closeFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/files/${fileId}/close`, {
      method: 'POST'
    });
  }

  // File System Operations

  /**
   * Get directory tree
   */
  async getDirectoryTree(path: string = '/'): Promise<DirectoryTree> {
    // Call the correct backend endpoint
    const response = await this.makeRequest(`/api/files?path=${encodeURIComponent(path)}`);
    const files = response.data || [];
    // Convert the flat file list to a DirectoryTree structure
    const tree: DirectoryTree = {
      path: path,
      name: path === '/' ? 'root' : path.split('/').pop() || 'root',
      type: 'directory',
      children: files.map((file: any) => ({
        path: file.path,
        name: file.name,
        type: file.type === 'directory' || file.is_directory ? 'directory' : 'file',
        size: file.size,
        modified_at: file.modified_at
      })),
      modified_at: new Date().toISOString()
    };
    return tree;
  }

  /**
   * Get file info
   */
  async getFileInfo(path: string): Promise<FileInfo> {
  const response = await this.makeRequest(`/api/files/info?path=${encodeURIComponent(path)}`);
  return response.data as FileInfo;
  }

  /**
   * Read file from filesystem
   */
  async readFile(path: string): Promise<string> {
  const response = await this.makeRequest(`/api/files/content?path=${encodeURIComponent(path)}`);
  // REST API returns { success, data: { path, content } }
  return (response.data?.content ?? '') as string;
  }

  /**
   * Write file to filesystem
   */
  async writeFile(path: string, content: string): Promise<void> {
    // REST API uses POST /api/files for create/write and PUT /api/files for update
    return this.makeRequest('/api/files', {
      method: 'POST',
      body: JSON.stringify({ path, content, encoding: 'utf-8', create_dirs: true })
    });
  }

  /**
   * Create directory
   */
  async createDirectory(path: string): Promise<void> {
    // REST API uses POST /api/files with type: 'directory'
    return this.makeRequest('/api/files', {
      method: 'POST',
      body: JSON.stringify({ path, type: 'directory', create_dirs: true })
    });
  }

  /**
   * Delete file or directory
   */
  async deleteFileSystem(path: string): Promise<void> {
    // REST API uses DELETE /api/files?path=...
    return this.makeRequest(`/api/files?path=${encodeURIComponent(path)}`, {
      method: 'DELETE'
    });
  }

  /**
   * Move/rename file or directory
   */
  async moveFileSystem(oldPath: string, newPath: string): Promise<void> {
    const response = await this.makeRequest('/api/files/move', {
      method: 'POST',
      body: JSON.stringify({
        source_path: oldPath,
        destination_path: newPath,
        overwrite: false,
      })
    });

    if (!response?.success) {
      throw new Error(response?.message || 'Failed to move file');
    }
  }

  /**
   * Search files
   */
  async searchFiles(query: string, path?: string): Promise<FileSearchResult[]> {
    const body: any = { query };
    if (path) body.path = path;
    const response = await this.makeRequest('/api/files/search', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    return response.data as FileSearchResult[];
  }

  // Terminal Operations

  /**
   * Get all terminal sessions
   */
  async getTerminals(): Promise<TerminalSession[]> {
    const response = await this.makeRequest('/api/terminals');
    return response.data;
  }

  /**
   * Create new terminal session
   */
  async createTerminal(config: TerminalConfig = {}): Promise<TerminalSession> {
    const response = await this.makeRequest('/api/terminals', {
      method: 'POST',
      body: JSON.stringify(config)
    });
    return response.data;
  }

  /**
   * Get terminal session
   */
  async getTerminal(terminalId: string): Promise<TerminalSession> {
    const response = await this.makeRequest(`/api/terminals/${terminalId}`);
    return response.data;
  }

  /**
   * Start terminal session
   */
  async startTerminal(terminalId: string): Promise<void> {
    return this.makeRequest(`/api/terminals/${terminalId}/start`, {
      method: 'POST'
    });
  }

  /**
   * Delete terminal session
   */
  async deleteTerminal(terminalId: string): Promise<void> {
    return this.makeRequest(`/api/terminals/${terminalId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Destroy terminal session (alias for deleteTerminal)
   */
  async destroyTerminal(terminalId: string): Promise<void> {
    return this.deleteTerminal(terminalId);
  }

  /**
   * Send input to terminal
   */
  async sendTerminalInput(terminalId: string, input: string): Promise<void> {
    return this.makeRequest(`/api/terminals/${terminalId}/input`, {
      method: 'POST',
      body: JSON.stringify({ input })
    });
  }

  /**
   * Resize terminal
   */
  async resizeTerminal(terminalId: string, rows: number, cols: number): Promise<void> {
    return this.makeRequest(`/api/terminals/${terminalId}/resize`, {
      method: 'POST',
      body: JSON.stringify({ rows, cols })
    });
  }

  /**
   * Set active terminal
   */
  async setActiveTerminal(terminalId: string): Promise<void> {
    return this.makeRequest(`/api/terminals/${terminalId}/activate`, {
      method: 'POST'
    });
  }

  // Panel Operations (Backend doesn't have these endpoints)
  /**
   * Get all panels
   */
  async getPanels(): Promise<WorkspacePanel[]> {
    return [];
  }

  /**
   * Create new panel
   */
  async createPanel(panel: Partial<WorkspacePanel>): Promise<WorkspacePanel> {
    return {
      id: `panel-${Date.now()}`,
      type: 'editor',
      title: 'New Panel',
      position: { x: 0, y: 0, width: 400, height: 300 },
      is_active: false,
      config: {},
      ...panel
    };
  }

  /**
   * Get panel by ID
   */
  async getPanel(panelId: string): Promise<WorkspacePanel> {
    return {
      id: panelId,
      type: 'editor',
      title: 'Panel',
      position: { x: 0, y: 0, width: 400, height: 300 },
      is_active: false,
      config: {}
    };
  }

  /**
   * Update panel
   */
  async updatePanel(panelId: string, updates: Partial<WorkspacePanel>): Promise<WorkspacePanel> {
    return { ...this.getPanel(panelId), ...updates };
  }

  /**
   * Delete panel
   */
  async deletePanel(panelId: string): Promise<void> {
    // No-op since backend doesn't support this
  }

  /**
   * Set active panel
   */
  async setActivePanel(panelId: string): Promise<void> {
    // No-op since backend doesn't support this
  }

  // Layout Operations (Backend doesn't have these endpoints)
  /**
   * Get workspace layout
   */
  async getLayout(): Promise<WorkspaceLayout> {
    return {
      id: 'default',
      name: 'Default Layout',
      panels: [],
      created_at: new Date().toISOString(),
      is_default: true
    };
  }

  /**
   * Update workspace layout
   */
  async updateLayout(layout: Partial<WorkspaceLayout>): Promise<WorkspaceLayout> {
    return { ...this.getLayout(), ...layout };
  }

  /**
   * Get layout by ID
   */
  async getLayoutById(layoutId: string): Promise<WorkspaceLayout> {
    return {
      id: layoutId,
      name: 'Layout',
      panels: [],
      created_at: new Date().toISOString(),
      is_default: false
    };
  }

  /**
   * Delete layout
   */
  async deleteLayout(layoutId: string): Promise<void> {
    // No-op since backend doesn't support this
  }

  // Code Execution

  /**
   * Execute code
   */
  async executeCode(request: CodeExecutionRequest): Promise<CodeExecutionResult> {
    return this.makeRequest('/api/code/execute', {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  /**
   * Get execution history
   */
  async getExecutionHistory(): Promise<CodeExecutionResult[]> {
    return this.makeRequest('/api/code/history');
  }

  /**
   * Clear execution history
   */
  async clearExecutionHistory(): Promise<void> {
    return this.makeRequest('/api/code/history', {
      method: 'DELETE'
    });
  }
}

import { configService, getCurrentConfig } from './config-service';

// Default configuration with dynamic config support
const getDefaultConfig = async (): Promise<BackendConfig> => {
  try {
    // First try to get dynamic configuration from the backend
    const config = await configService.getConfig();
    console.log('🔧 Using dynamic config for BackendClient:', config);
    
    return {
      websocket_url: config.ws_url,
      http_base_url: config.api_url,
      reconnect_attempts: 5,
      reconnect_delay: 1000,
      request_timeout: 10000,
      heartbeat_interval: 30000
    };
  } catch (error) {
    console.warn('⚠️  Failed to get dynamic config for BackendClient, using fallbacks:', error);
    
    // Fallback to environment variables or dynamic detection
    let websocketUrl = import.meta.env.VITE_WS_URL;
    let httpBaseUrl = import.meta.env.VITE_API_URL;
    
    // SAAS PROTOCOL FIX: Handle environment variable protocol conversion
    if (websocketUrl && typeof window !== 'undefined') {
      try {
        const wsUrl = new URL(websocketUrl);
        const currentProtocol = window.location.protocol;
        const shouldUseSecure = currentProtocol === 'https:';
        const finalProtocol = shouldUseSecure ? 'wss:' : wsUrl.protocol;
        
        websocketUrl = `${finalProtocol}//${wsUrl.host}${wsUrl.pathname}${wsUrl.search}`;
        if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
          console.log(`🔒 BackendClient fallback protocol: page=${currentProtocol}, env=${wsUrl.protocol}, final=${finalProtocol}`);
        }
      } catch {
        // If parsing fails, keep original value
      }
    }
    
    // Final fallback to dynamic detection
    if (!websocketUrl && typeof window !== 'undefined') {
      websocketUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
    } else if (!websocketUrl) {
      websocketUrl = 'ws://localhost:8000/ws';
    }
    
    if (!httpBaseUrl && typeof window !== 'undefined') {
      httpBaseUrl = `${window.location.protocol}//${window.location.host}/api`;
    } else if (!httpBaseUrl) {
      httpBaseUrl = 'http://localhost:8000/api';
    }

    return {
      websocket_url: websocketUrl,
      http_base_url: httpBaseUrl,
      reconnect_attempts: 5,
      reconnect_delay: 1000,
      request_timeout: 10000,
      heartbeat_interval: 30000
    };
  }
};

// Singleton instance
let backendClient: BackendClient | null = null;

/**
 * Get the singleton backend client instance
 */
export async function getBackendClient(config?: Partial<BackendConfig>): Promise<BackendClient> {
  if (!backendClient) {
    const defaultConfig = await getDefaultConfig();
    const finalConfig = { ...defaultConfig, ...config };
    backendClient = new BackendClient(finalConfig);
    console.log('🔄 BackendClient initialized with config:', finalConfig);
  }
  return backendClient;
}

/**
 * Reset the singleton instance (useful for testing)
 */
export function resetBackendClient(): void {
  backendClient = null;
}

export default BackendClient;
