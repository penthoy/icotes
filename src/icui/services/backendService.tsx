/**
 * ICUI Backend Service
 * 
 * Centralized backend client for all ICUI components.
 * Extends the base FileClient with ICUI-specific operations.
 * Eliminates code duplication across ICUIEditor, ICUIExplorer, ICUIBaseFooter.
 */

import { FileClient, ConnectionStatus } from './backendClient';

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

/**
 * Centralized backend service for ICUI components
 * Provides file operations, connection management, and workspace utilities
 */
export class ICUIBackendService extends FileClient {
  private _initialized = false;

  /**
   * Ensure service is initialized before operations
   */
  private async ensureInitialized(): Promise<void> {
    if (!this._initialized) {
      console.log('[ICUIBackendService] Auto-initializing service...');
      await this.initialize();
      this._initialized = true;
    }
  }
  
  /**
   * Get workspace files for editor component
   */
  async getWorkspaceFiles(workspacePath: string): Promise<ICUIFile[]> {
    await this.ensureInitialized();
    
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files?path=${encodeURIComponent(workspacePath)}`);
        const result = await this.handleResponse<any>(response);
        
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
            language: this.getLanguageFromExtension(item.name),
            content: '', // Content will be loaded separately
            modified: false,
            path: item.path
          }));
      },
      async () => {
        // Fallback: return empty array
        return [];
      },
      'Workspace file listing'
    );
  }

  /**
   * Get workspace directory structure for explorer component
   */
  async getDirectoryContents(path: string = '/'): Promise<ICUIFileNode[]> {
    await this.ensureInitialized();
    
    // Getting directory contents for path
    
    return this.executeWithFallback(
      async () => {
        const url = `${this.baseUrl}/api/files?path=${encodeURIComponent(path)}`;
        // Fetching from backend URL
        
        const response = await fetch(url);
        // Response status received
        
        const result = await response.json();
        // Parsed result received
        
        if (!result.success) {
          throw new Error(result.message || 'Failed to get directory contents');
        }
        
        const fileList = result.data || result.files || [];
        // File list retrieved
        
        // Convert backend format to FileNode format
        const nodes: ICUIFileNode[] = fileList.map((file: any) => ({
          id: file.path || file.id,
          name: file.name,
          type: (file.is_directory || file.isDirectory) ? 'folder' : 'file',
          path: file.path,
          size: file.size,
          modified: file.modified
        }));
        
        // Converted nodes to FileNode format                // Sort nodes: directories first, then files (alphabetically within each group)
        const sortedNodes = nodes.sort((a, b) => {
          if (a.type === 'folder' && b.type === 'file') return -1;
          if (a.type === 'file' && b.type === 'folder') return 1;
          return a.name.localeCompare(b.name);
        });
        
        // Returning sorted nodes
        return sortedNodes;
      },
      async () => {
        // Fallback: return empty array
        // Using fallback - returning empty array
        return [];
      },
      'Directory listing'
    );
  }

  /**
   * Get file with content for editor
   */
  async getFile(filePath: string): Promise<ICUIFile> {
    const content = await this.getFileContent(filePath);
    const filename = filePath.split('/').pop() || 'untitled';
    
    return {
      id: filePath,
      name: filename,
      language: this.getLanguageFromExtension(filename),
      content: content,
      modified: false,
      path: filePath
    };
  }

  /**
   * Execute code in backend
   */
  async executeCode(code: string, language: string, filePath?: string): Promise<any> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/execute`, {
          method: 'POST',
          body: JSON.stringify({ 
            code, 
            language,
            file_path: filePath || 'untitled'
          }),
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

  /**
   * Create file in workspace
   */
  async createFile(path: string, content: string = ''): Promise<void> {
    await this.saveFile(path, content);
  }

  /**
   * Create directory in workspace
   */
  async createDirectory(path: string): Promise<void> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/files`, {
          method: 'POST',
          body: JSON.stringify({ 
            path, 
            is_directory: true 
          }),
        });
        await this.handleResponse(response);
      },
      async () => {
        // Fallback: no-op
        console.warn('Directory creation not available in fallback mode');
      },
      'Directory creation'
    );
  }

  /**
   * Delete file or directory
   */
  async deleteFile(path: string): Promise<void> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/files?path=${encodeURIComponent(path)}`, {
          method: 'DELETE',
        });
        await this.handleResponse(response);
      },
      async () => {
        // Fallback: no-op
        console.warn('File deletion not available in fallback mode');
      },
      'File deletion'
    );
  }

  /**
   * Get language from file extension
   */
  private getLanguageFromExtension(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'js':
        return 'javascript';
      case 'ts':
        return 'typescript';
      case 'py':
        return 'python';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'json':
        return 'json';
      case 'md':
        return 'markdown';
      default:
        return 'text';
    }
  }
}

// Singleton instance for use across ICUI components
export const icuiBackendService = new ICUIBackendService();

// Re-export types for convenience
export type { ConnectionStatus };
