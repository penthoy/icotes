/**
 * File Management Service
 * 
 * Reusable file management service for the ICUI framework.
 * Extracted from simpleeditor.tsx patterns with fallback logic,
 * language detection, and workspace management.
 */

import { BackendClient } from './backendClient';
import { notificationService } from './notificationService';

export interface FileInfo {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
  path?: string;
}

export interface FileServiceConfig {
  workspacePath?: string;
  autoSaveDelay?: number;
  enableAutoSave?: boolean;
}

export interface FileServiceCapabilities {
  icpy_files: boolean;
  file_upload: boolean;
  file_download: boolean;
  file_crud: boolean;
}

export class FileService extends BackendClient {
  private fileConfig: Required<FileServiceConfig>;
  private autoSaveTimeouts: Map<string, NodeJS.Timeout> = new Map();
  private modificationCallbacks: Set<(fileId: string, modified: boolean) => void> = new Set();

  constructor(config: FileServiceConfig = {}) {
    super();
    
    this.fileConfig = {
      workspacePath: config.workspacePath || '/home/penthoy/ilaborcode/workspace',
      autoSaveDelay: config.autoSaveDelay || 2000,
      enableAutoSave: config.enableAutoSave !== false, // Default to true
      ...config
    };
  }

  /**
   * Detect service capabilities specific to file operations
   */
  protected async detectServiceCapabilities(services: Record<string, any>): Promise<Record<string, any>> {
    const capabilities: Record<string, any> = {
      icpy_files: false,
      file_upload: false,
      file_download: false,
      file_crud: false
    };
    
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
    capabilities.file_crud = capabilities.icpy_files || services.files || false;
    
    return capabilities;
  }

  /**
   * List files in a directory
   */
  async listFiles(path: string = this.fileConfig.workspacePath): Promise<FileInfo[]> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files?path=${encodeURIComponent(path)}`);
        const data = await this.handleResponse<any>(response);
        
        if (data.success && data.data) {
          // Convert ICPY file format to FileInfo format
          return data.data
            .filter((file: any) => !file.is_directory) // Filter out directories
            .map((file: any, index: number) => ({
              id: file.path || `file_${index}`,
              name: file.name,
              language: this.getLanguageFromExtension(file.name),
              content: '', // Content will be loaded separately
              modified: false,
              path: file.path
            }));
        }
        return [];
      },
      async () => {
        // Fallback: return sample files
        return this.getSampleFiles();
      },
      'File listing'
    );
  }

  /**
   * Get file content
   */
  async getFile(fileId: string): Promise<FileInfo> {
    return this.executeWithFallback<FileInfo>(
      async (): Promise<FileInfo> => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files/content?path=${encodeURIComponent(fileId)}`);
        const data = await this.handleResponse<any>(response);
        
        if (data.success && data.data) {
          const filename = fileId.split('/').pop() || 'untitled';
          return {
            id: fileId,
            name: filename,
            language: this.getLanguageFromExtension(filename),
            content: data.data.content || '',
            modified: false,
            path: fileId
          };
        }
        
        throw new Error('Invalid response format');
      },
      async (): Promise<FileInfo> => {
        // Fallback: try to find in sample files
        const sampleFiles = this.getSampleFiles();
        const file = sampleFiles.find(f => f.id === fileId);
        if (file) {
          return file;
        }
        throw new Error('File not found');
      },
      'File content retrieval'
    );
  }

  /**
   * Save file content
   */
  async saveFile(file: FileInfo, skipNotification: boolean = false): Promise<void> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files`, {
          method: 'PUT',
          body: JSON.stringify({
            path: file.path || file.name,
            content: file.content,
            encoding: 'utf-8',
            create_dirs: true
          }),
        });
        
        const data = await this.handleResponse<any>(response);
        if (!data.success) {
          throw new Error(data.message || 'Save failed');
        }
        
        if (!skipNotification) {
          notificationService.success(`Saved ${file.name}`);
        }
      },
      async () => {
        // Fallback: simulate save
        if (!skipNotification) {
          notificationService.warning(`${file.name} saved locally only (backend unavailable)`);
        }
      },
      'File save'
    );
  }

  /**
   * Create a new file
   */
  async createFile(name: string, language: string = 'javascript', initialContent: string = ''): Promise<FileInfo> {
    return this.executeWithFallback(
      async () => {
        const extension = this.getExtensionFromLanguage(language);
        const filename = name.includes('.') ? name : `${name}.${extension}`;
        const filepath = `${this.fileConfig.workspacePath}/${filename}`;
        
        const content = initialContent || `// New ${language} file: ${filename}\n\n`;
        
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files`, {
          method: 'POST',
          body: JSON.stringify({
            path: filepath,
            content: content,
            encoding: 'utf-8',
            create_dirs: true
          }),
        });
        
        const data = await this.handleResponse<any>(response);
        if (!data.success) {
          throw new Error(data.message || 'Create failed');
        }
        
        notificationService.success(`Created ${filename}`);
        
        return {
          id: filepath,
          name: filename,
          language,
          content: content,
          modified: false,
          path: filepath
        };
      },
      async () => {
        // Fallback: create client-side only
        const extension = this.getExtensionFromLanguage(language);
        const filename = name.includes('.') ? name : `${name}.${extension}`;
        const content = initialContent || `// New ${language} file: ${filename}\n\n`;
        
        notificationService.warning(`${filename} created locally only (backend unavailable)`);
        
        const fileId = `${Date.now()}_${filename}`;
        return {
          id: fileId,
          name: filename,
          language,
          content: content,
          modified: false,
          path: filename
        };
      },
      'File creation'
    );
  }

  /**
   * Delete a file
   */
  async deleteFile(fileId: string): Promise<void> {
    return this.executeWithFallback(
      async () => {
        const response = await this.fetchWithRetry(`${this.baseUrl}/api/files?path=${encodeURIComponent(fileId)}`, {
          method: 'DELETE'
        });
        
        const data = await this.handleResponse<any>(response);
        if (!data.success) {
          throw new Error(data.message || 'Delete failed');
        }
        
        notificationService.success(`Deleted file`);
      },
      async () => {
        // Fallback: simulate deletion
        notificationService.warning(`File deletion simulated (backend unavailable)`);
      },
      'File deletion'
    );
  }

  /**
   * Auto-save file with debouncing
   */
  enableAutoSave(file: FileInfo, onSaved?: (success: boolean) => void): void {
    if (!this.fileConfig.enableAutoSave) return;
    
    // Clear existing timeout for this file
    const existingTimeout = this.autoSaveTimeouts.get(file.id);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    const timeout = setTimeout(async () => {
      try {
        await this.saveFile(file, true); // Skip notification for auto-save
        this.notifyModification(file.id, false);
        notificationService.success(`Auto-saved ${file.name}`, { duration: 1500 });
        onSaved?.(true);
      } catch (error) {
        notificationService.error(`Auto-save failed: ${error.message}`);
        onSaved?.(false);
      }
      
      this.autoSaveTimeouts.delete(file.id);
    }, this.fileConfig.autoSaveDelay);

    this.autoSaveTimeouts.set(file.id, timeout);
  }

  /**
   * Cancel auto-save for a file
   */
  cancelAutoSave(fileId: string): void {
    const timeout = this.autoSaveTimeouts.get(fileId);
    if (timeout) {
      clearTimeout(timeout);
      this.autoSaveTimeouts.delete(fileId);
    }
  }

  /**
   * Track file modification state
   */
  markAsModified(fileId: string, modified: boolean = true): void {
    this.notifyModification(fileId, modified);
  }

  /**
   * Subscribe to file modification changes
   */
  onModificationChange(callback: (fileId: string, modified: boolean) => void): () => void {
    this.modificationCallbacks.add(callback);
    return () => {
      this.modificationCallbacks.delete(callback);
    };
  }

  /**
   * Get language from file extension
   */
  getLanguageFromExtension(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'js': return 'javascript';
      case 'ts': return 'typescript';
      case 'tsx': return 'typescript';
      case 'jsx': return 'javascript';
      case 'py': return 'python';
      case 'html': return 'html';
      case 'htm': return 'html';
      case 'css': return 'css';
      case 'scss': return 'scss';
      case 'sass': return 'sass';
      case 'less': return 'less';
      case 'json': return 'json';
      case 'md': return 'markdown';
      case 'markdown': return 'markdown';
      case 'xml': return 'xml';
      case 'yaml': return 'yaml';
      case 'yml': return 'yaml';
      case 'toml': return 'toml';
      case 'sh': return 'bash';
      case 'bash': return 'bash';
      case 'zsh': return 'bash';
      case 'fish': return 'bash';
      case 'sql': return 'sql';
      case 'php': return 'php';
      case 'rb': return 'ruby';
      case 'go': return 'go';
      case 'rs': return 'rust';
      case 'java': return 'java';
      case 'c': return 'c';
      case 'cpp': return 'cpp';
      case 'cc': return 'cpp';
      case 'cxx': return 'cpp';
      case 'h': return 'c';
      case 'hpp': return 'cpp';
      default: return 'text';
    }
  }

  /**
   * Get file extension from language
   */
  getExtensionFromLanguage(language: string): string {
    switch (language) {
      case 'javascript': return 'js';
      case 'typescript': return 'ts';
      case 'python': return 'py';
      case 'html': return 'html';
      case 'css': return 'css';
      case 'scss': return 'scss';
      case 'sass': return 'sass';
      case 'less': return 'less';
      case 'json': return 'json';
      case 'markdown': return 'md';
      case 'xml': return 'xml';
      case 'yaml': return 'yaml';
      case 'toml': return 'toml';
      case 'bash': return 'sh';
      case 'sql': return 'sql';
      case 'php': return 'php';
      case 'ruby': return 'rb';
      case 'go': return 'go';
      case 'rust': return 'rs';
      case 'java': return 'java';
      case 'c': return 'c';
      case 'cpp': return 'cpp';
      default: return 'txt';
    }
  }

  /**
   * Clean up resources
   */
  override destroy(): void {
    // Clear all auto-save timeouts
    for (const timeout of this.autoSaveTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.autoSaveTimeouts.clear();
    this.modificationCallbacks.clear();
    
    super.destroy();
  }

  /**
   * Get sample files for fallback mode
   */
  private getSampleFiles(): FileInfo[] {
    return [
      {
        id: 'example.js',
        name: 'example.js',
        language: 'javascript',
        content: `// Example JavaScript file\nconsole.log("Hello from File Service!");`,
        modified: false,
        path: 'example.js'
      },
      {
        id: 'test.py',
        name: 'test.py',
        language: 'python',
        content: `# Example Python file\nprint("Hello from File Service!")`,
        modified: false,
        path: 'test.py'
      },
      {
        id: 'README.md',
        name: 'README.md',
        language: 'markdown',
        content: `# File Service Demo\n\nThis is a demo file from the ICUI File Service.`,
        modified: false,
        path: 'README.md'
      }
    ];
  }

  /**
   * Notify modification state changes
   */
  private notifyModification(fileId: string, modified: boolean): void {
    this.modificationCallbacks.forEach(callback => callback(fileId, modified));
  }
}

// Export convenience instance
export const fileService = new FileService();

// Export default instance
export default fileService;
