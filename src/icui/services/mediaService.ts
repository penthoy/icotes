/**
 * Media Service - Phase 2 Frontend Core
 * 
 * Abstract API interface for media operations across all components.
 * Provides unified upload lifecycle, validation, and error handling.
 */

import { configService } from '../../services/config-service';

export interface MediaAttachment {
  id: string;
  kind: 'image' | 'audio' | 'file';
  path: string;
  mime: string;
  size: number;
  meta?: Record<string, any>;
}

export interface UploadResult {
  id: string;
  type: string;
  rel_path: string;
  mime: string;
  size: number;
}

export interface MediaFile {
  name: string;
  rel_path: string;
  size: number;
  created_at: string;
  mime: string;
}

export interface MediaError {
  code: string;
  message: string;
  file?: string;
}

class MediaService {
  private apiUrl: string = '';
  private initialized: boolean = false;

  constructor() {
    // Initialize URLs using the same configService as ICUIBackendService
    this.initializeApiUrl();
  }
  
  async exportAttachment(attachmentId: string, destPath: string): Promise<{ success: boolean; path: string }> {
    const cfg = await configService.getConfig();
    const base = cfg.api_url || '/api';
    const res = await fetch(`${base}/media/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attachment_id: attachmentId, dest_path: destPath }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Export failed (${res.status}): ${text}`);
    }
    return res.json();
  }

  /**
   * Initialize API URL using dynamic configuration
   */
  private async initializeApiUrl(): Promise<void> {
    try {
      const config = await configService.getConfig();
      this.apiUrl = config.api_url;
      this.initialized = true;
      console.log('📁 MediaService using dynamic API URL:', this.apiUrl);
    } catch (error) {
      console.warn('⚠️  Failed to get dynamic config for MediaService, using fallback:', error);
      
      // Fallback to environment or dynamic detection
      const envApiUrl = import.meta.env.VITE_API_URL;
      if (envApiUrl) {
        this.apiUrl = envApiUrl;
      } else {
        // Dynamic detection
        if (typeof window !== 'undefined') {
          const protocol = window.location.protocol;
          const host = window.location.host;
          this.apiUrl = `${protocol}//${host}/api`;
        } else {
          this.apiUrl = '/api';
        }
      }
      
      this.initialized = true;
      console.log('📁 MediaService using fallback API URL:', this.apiUrl);
    }
  }

  /**
   * Ensure API URL is initialized before making requests
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initializeApiUrl();
    }
  }

  /**
   * Upload multiple files
   */
  async upload(files: FileList | File[]): Promise<UploadResult[]> {
    await this.ensureInitialized();
    
    const formData = new FormData();
    
    // Convert FileList to array if needed
    const fileArray = Array.from(files);
    
    fileArray.forEach((file) => {
      formData.append('file', file);
    });

    const response = await fetch(`${this.apiUrl}/media/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error: MediaError = await response.json().catch(() => ({
        code: 'upload_failed',
        message: `Upload failed with status ${response.status}`,
      }));
      throw new Error(error.message);
    }

    const result = await response.json();
    
    // Handle single file response (wrap in array)
    if (result.attachment) {
      return [result.attachment];
    }
    
    // Handle multiple file response
    return result.attachments || [];
  }

  /**
   * List files by type
   */
  async list(type: 'images' | 'audio' | 'files'): Promise<MediaFile[]> {
    await this.ensureInitialized();
    
    const response = await fetch(`${this.apiUrl}/media/list/${type}`);

    if (!response.ok) {
      throw new Error(`Failed to list ${type}: ${response.statusText}`);
    }

    const result = await response.json();
    return result.files || [];
  }

  /**
   * Download a single file
   */
  async download(type: string, filename: string): Promise<void> {
    await this.ensureInitialized();
    
    const url = `${this.apiUrl}/media/${type}/${filename}`;
    
    // Create temporary download link
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Get file URL for inline display
   */
  getFileUrl(type: string, filename: string): string {
    // Use initialized URL or fallback for synchronous access
    const url = this.apiUrl || this.getFallbackApiUrl();
    return `${url}/media/${type}/${filename}`;
  }

  /**
   * Get file URL from attachment
   */
  getAttachmentUrl(attachment: MediaAttachment): string {
    // Use the attachment ID to get file via the backend API
    const url = this.apiUrl || this.getFallbackApiUrl();
    return `${url}/media/file/${attachment.id}`;
  }

  /**
   * Get fallback API URL for synchronous methods
   */
  private getFallbackApiUrl(): string {
    const envApiUrl = import.meta.env.VITE_API_URL;
    if (envApiUrl) {
      return envApiUrl;
    }
    
    // Dynamic detection
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol;
      const host = window.location.host;
      return `${protocol}//${host}/api`;
    }
    
    return '/api';
  }

  /**
   * Delete a file
   */
  async delete(type: string, filename: string): Promise<{ success: boolean; referenced?: boolean }> {
    await this.ensureInitialized();
    
    const response = await fetch(`${this.apiUrl}/media/${type}/${filename}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete file: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Create and download a zip of multiple files
   */
  async zip(paths: string[]): Promise<void> {
    await this.ensureInitialized();
    
    const response = await fetch(`${this.apiUrl}/media/zip`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ paths }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create zip: ${response.statusText}`);
    }

    // Download the zip file
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `media-files-${Date.now()}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up
    URL.revokeObjectURL(url);
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    // Get limits from environment or use defaults
    const maxImageMB = parseInt(import.meta.env.VITE_MEDIA_MAX_FILE_SIZE_MB || '25');
    const allowedTypes = (import.meta.env.VITE_MEDIA_ALLOWED_TYPES || 'image/*,video/*,audio/*,.pdf').split(',');

    // Size check
    const maxBytes = maxImageMB * 1024 * 1024;
    if (file.size > maxBytes) {
      return {
        valid: false,
        error: `File size exceeds ${maxImageMB}MB limit`,
      };
    }

    // Type check
    const isAllowed = allowedTypes.some(allowedType => {
      if (allowedType.endsWith('/*')) {
        const prefix = allowedType.slice(0, -2);
        return file.type.startsWith(prefix);
      }
      if (allowedType.startsWith('.')) {
        return file.name.toLowerCase().endsWith(allowedType.toLowerCase());
      }
      return file.type === allowedType;
    });

    if (!isAllowed) {
      return {
        valid: false,
        error: `File type ${file.type} is not allowed`,
      };
    }

    return { valid: true };
  }
}

// Export singleton instance
export const mediaService = new MediaService();
export default mediaService;
