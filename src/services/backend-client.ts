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
   * Get current workspace state
   */
  async getWorkspaceState(): Promise<WorkspaceState> {
    return this.makeRequest('/api/workspace/state');
  }

  /**
   * Create a new workspace
   */
  async createWorkspace(name: string, description?: string): Promise<WorkspaceState> {
    return this.makeRequest('/api/workspace', {
      method: 'POST',
      body: JSON.stringify({ name, description })
    });
  }

  /**
   * Update workspace information
   */
  async updateWorkspace(updates: Partial<WorkspaceState>): Promise<WorkspaceState> {
    return this.makeRequest('/api/workspace', {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  /**
   * Delete workspace
   */
  async deleteWorkspace(): Promise<void> {
    return this.makeRequest('/api/workspace', {
      method: 'DELETE'
    });
  }

  /**
   * Get workspace preferences
   */
  async getPreferences(): Promise<WorkspacePreferences> {
    return this.makeRequest('/api/workspace/preferences');
  }

  /**
   * Update workspace preferences
   */
  async updatePreferences(preferences: Partial<WorkspacePreferences>): Promise<WorkspacePreferences> {
    return this.makeRequest('/api/workspace/preferences', {
      method: 'PUT',
      body: JSON.stringify(preferences)
    });
  }

  /**
   * Get workspace statistics
   */
  async getWorkspaceStatistics(): Promise<Record<string, any>> {
    return this.makeRequest('/api/workspace/statistics');
  }

  // File Operations

  /**
   * Get file content
   */
  async getFile(fileId: string): Promise<WorkspaceFile> {
    return this.makeRequest(`/api/workspace/files/${fileId}`);
  }

  /**
   * Create a new file
   */
  async createFile(path: string, content: string = '', language?: string): Promise<WorkspaceFile> {
    return this.makeRequest('/api/workspace/files', {
      method: 'POST',
      body: JSON.stringify({ path, content, language })
    });
  }

  /**
   * Update file content
   */
  async updateFile(fileId: string, content: string): Promise<WorkspaceFile> {
    return this.makeRequest(`/api/workspace/files/${fileId}`, {
      method: 'PUT',
      body: JSON.stringify({ content })
    });
  }

  /**
   * Delete a file
   */
  async deleteFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/files/${fileId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Get all files in workspace
   */
  async getFiles(): Promise<WorkspaceFile[]> {
    return this.makeRequest('/api/workspace/files');
  }

  /**
   * Set active file
   */
  async setActiveFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/files/${fileId}/activate`, {
      method: 'POST'
    });
  }

  /**
   * Save file (same as update but with different semantic meaning)
   */
  async saveFile(fileId: string, content: string): Promise<WorkspaceFile> {
    return this.updateFile(fileId, content);
  }

  /**
   * Close file
   */
  async closeFile(fileId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/files/${fileId}/close`, {
      method: 'POST'
    });
  }

  // File System Operations

  /**
   * Get directory tree
   */
  async getDirectoryTree(path: string = '/'): Promise<DirectoryTree> {
    return this.makeRequest(`/api/filesystem/tree?path=${encodeURIComponent(path)}`);
  }

  /**
   * Get file info
   */
  async getFileInfo(path: string): Promise<FileInfo> {
    return this.makeRequest(`/api/filesystem/info?path=${encodeURIComponent(path)}`);
  }

  /**
   * Read file from filesystem
   */
  async readFile(path: string): Promise<string> {
    return this.makeRequest(`/api/filesystem/read?path=${encodeURIComponent(path)}`);
  }

  /**
   * Write file to filesystem
   */
  async writeFile(path: string, content: string): Promise<void> {
    return this.makeRequest('/api/filesystem/write', {
      method: 'POST',
      body: JSON.stringify({ path, content })
    });
  }

  /**
   * Create directory
   */
  async createDirectory(path: string): Promise<void> {
    return this.makeRequest('/api/filesystem/directory', {
      method: 'POST',
      body: JSON.stringify({ path })
    });
  }

  /**
   * Delete file or directory
   */
  async deleteFileSystem(path: string): Promise<void> {
    return this.makeRequest('/api/filesystem/delete', {
      method: 'DELETE',
      body: JSON.stringify({ path })
    });
  }

  /**
   * Move/rename file or directory
   */
  async moveFileSystem(oldPath: string, newPath: string): Promise<void> {
    return this.makeRequest('/api/filesystem/move', {
      method: 'POST',
      body: JSON.stringify({ old_path: oldPath, new_path: newPath })
    });
  }

  /**
   * Search files
   */
  async searchFiles(query: string, path?: string): Promise<FileSearchResult[]> {
    const params = new URLSearchParams({ query });
    if (path) params.append('path', path);
    return this.makeRequest(`/api/filesystem/search?${params}`);
  }

  // Terminal Operations

  /**
   * Get all terminal sessions
   */
  async getTerminals(): Promise<TerminalSession[]> {
    return this.makeRequest('/api/workspace/terminals');
  }

  /**
   * Create new terminal session
   */
  async createTerminal(config: TerminalConfig = {}): Promise<TerminalSession> {
    return this.makeRequest('/api/workspace/terminals', {
      method: 'POST',
      body: JSON.stringify(config)
    });
  }

  /**
   * Get terminal session
   */
  async getTerminal(terminalId: string): Promise<TerminalSession> {
    return this.makeRequest(`/api/workspace/terminals/${terminalId}`);
  }

  /**
   * Delete terminal session
   */
  async deleteTerminal(terminalId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/terminals/${terminalId}`, {
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
    return this.makeRequest(`/api/workspace/terminals/${terminalId}/input`, {
      method: 'POST',
      body: JSON.stringify({ input })
    });
  }

  /**
   * Resize terminal
   */
  async resizeTerminal(terminalId: string, rows: number, cols: number): Promise<void> {
    return this.makeRequest(`/api/workspace/terminals/${terminalId}/resize`, {
      method: 'POST',
      body: JSON.stringify({ rows, cols })
    });
  }

  /**
   * Set active terminal
   */
  async setActiveTerminal(terminalId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/terminals/${terminalId}/activate`, {
      method: 'POST'
    });
  }

  // Panel Operations

  /**
   * Get all panels
   */
  async getPanels(): Promise<WorkspacePanel[]> {
    return this.makeRequest('/api/workspace/panels');
  }

  /**
   * Create new panel
   */
  async createPanel(panel: Omit<WorkspacePanel, 'id'>): Promise<WorkspacePanel> {
    return this.makeRequest('/api/workspace/panels', {
      method: 'POST',
      body: JSON.stringify(panel)
    });
  }

  /**
   * Update panel
   */
  async updatePanel(panelId: string, updates: Partial<WorkspacePanel>): Promise<WorkspacePanel> {
    return this.makeRequest(`/api/workspace/panels/${panelId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
  }

  /**
   * Delete panel
   */
  async deletePanel(panelId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/panels/${panelId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Set active panel
   */
  async setActivePanel(panelId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/panels/${panelId}/activate`, {
      method: 'POST'
    });
  }

  // Layout Operations

  /**
   * Get current layout
   */
  async getLayout(): Promise<WorkspaceLayout> {
    return this.makeRequest('/api/workspace/layout');
  }

  /**
   * Save layout
   */
  async saveLayout(layout: Omit<WorkspaceLayout, 'id' | 'created_at'>): Promise<WorkspaceLayout> {
    return this.makeRequest('/api/workspace/layout', {
      method: 'POST',
      body: JSON.stringify(layout)
    });
  }

  /**
   * Load layout
   */
  async loadLayout(layoutId: string): Promise<WorkspaceLayout> {
    return this.makeRequest(`/api/workspace/layout/${layoutId}`, {
      method: 'POST'
    });
  }

  /**
   * Delete layout
   */
  async deleteLayout(layoutId: string): Promise<void> {
    return this.makeRequest(`/api/workspace/layout/${layoutId}`, {
      method: 'DELETE'
    });
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

// Default configuration
const defaultConfig: BackendConfig = {
  websocket_url: 'ws://localhost:8000/ws',
  http_base_url: 'http://localhost:8000',
  reconnect_attempts: 5,
  reconnect_delay: 1000,
  request_timeout: 10000,
  heartbeat_interval: 30000
};

// Singleton instance
let backendClient: BackendClient | null = null;

/**
 * Get the singleton backend client instance
 */
export function getBackendClient(config?: Partial<BackendConfig>): BackendClient {
  if (!backendClient) {
    const finalConfig = { ...defaultConfig, ...config };
    backendClient = new BackendClient(finalConfig);
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
