/**
 * Media Upload Hook - Phase 2 Frontend Core
 * 
 * Queue state machine for upload lifecycle management:
 * pending -> uploading -> success/error
 * Supports progress tracking, cancellation, and retry logic.
 */

import React, { useState, useCallback, useRef } from 'react';
import { mediaService, UploadResult, MediaAttachment } from '../services/mediaService';
import { configService } from '../../services/config-service';

export type UploadStatus = 'pending' | 'uploading' | 'completed' | 'error';

export interface UploadItem {
  id: string;
  file: File;
  status: UploadStatus;
  progress: number;
  result?: UploadResult;
  error?: string;
  abortController?: AbortController;
  context?: 'chat' | 'explorer';
  destPath?: string; // for explorer context final workspace destination
}

export interface UseMediaUploadReturn {
  queue: UploadItem[];           // Alias for uploads
  uploads: UploadItem[];         // Original property
  isUploading: boolean;
  addFiles: (files: FileList | File[], options?: { context?: 'chat' | 'explorer'; destPath?: string }) => void;  // Add files to queue without uploading
  uploadAll: () => Promise<UploadResult[]>;      // Upload all pending files
  upload: (files: FileList | File[]) => Promise<UploadResult[]>; // Direct upload (legacy)
  removeFile: (id: string) => void;             // Remove from queue
  cancel: (id: string) => void;
  retry: (id: string) => void;
  clear: () => void;
  clearCompleted: () => void;
}

export function useMediaUpload(options: { autoStart?: boolean } = {}): UseMediaUploadReturn {
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const uploadId = useRef(0);
  const autoStart = options.autoStart ?? true;

  const isUploading = uploads.some(upload => upload.status === 'uploading' || upload.status === 'pending');

  const createUploadItem = useCallback((file: File, extra?: { context?: 'chat' | 'explorer'; destPath?: string }): UploadItem => {
    return {
      id: `upload-${++uploadId.current}`,
      file,
      status: 'pending',
      progress: 0,
      context: extra?.context,
      destPath: extra?.destPath,
    };
  }, []);

  const updateUpload = useCallback((id: string, updates: Partial<UploadItem>) => {
    setUploads(prev => prev.map(upload => 
      upload.id === id ? { ...upload, ...updates } : upload
    ));
  }, []);

  const uploadSingleFile = useCallback(async (uploadItem: UploadItem): Promise<UploadResult> => {
    const { id, file } = uploadItem;
    
    // Validate file first
    const validation = mediaService.validateFile(file);
    if (!validation.valid) {
      updateUpload(id, {
        status: 'error',
        error: validation.error,
      });
      throw new Error(validation.error);
    }

    // Create abort controller for cancellation
    const abortController = new AbortController();
    updateUpload(id, {
      status: 'uploading',
      progress: 0,
      abortController,
    });

    try {
      // Branch: direct explorer upload with destPath -> use uploadTo endpoint (no central duplicate + export)
      if (uploadItem.context === 'explorer' && uploadItem.destPath) {
        try {
          const direct = await mediaService.uploadTo(file, uploadItem.destPath);
          updateUpload(id, { status: 'completed', progress: 100, result: direct, abortController: undefined });
          return direct;
        } catch (e) {
          let msg: string;
          if (e instanceof Error) {
            msg = e.message;
          } else if (typeof e === 'string') {
            msg = `Direct upload failed: ${e}`;
          } else if (typeof e === 'object' && e !== null) {
            try {
              msg = `Direct upload failed: ${JSON.stringify(e)}`;
            } catch {
              msg = `Direct upload failed: ${e.toString()}`;
            }
          } else {
            msg = 'Direct upload failed: Unknown error';
          }
          updateUpload(id, { status: 'error', error: msg, abortController: undefined });
          throw e;
        }
      }

      // Default path: central storage first then optional export
      const result = await new Promise<UploadResult>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        // Progress tracking
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            updateUpload(id, { progress });
          }
        });

        // Handle completion
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve(response.attachment || response);
            } catch (e) {
              reject(new Error('Invalid response format'));
            }
          } else {
            try {
              const error = JSON.parse(xhr.responseText);
              reject(new Error(error.message || `Upload failed: ${xhr.status}`));
            } catch (e) {
              reject(new Error(`Upload failed: ${xhr.status}`));
            }
          }
        });

        // Handle errors
        xhr.addEventListener('error', () => {
          reject(new Error('Network error during upload'));
        });

        // Handle abort
        xhr.addEventListener('abort', () => {
          reject(new Error('Upload cancelled'));
        });

        // Set up cancellation
        abortController.signal.addEventListener('abort', () => {
          xhr.abort();
        });

        // Resolve API URL from centralized config (same as ICUIBackendService)
        // We cannot await here; fetch config then proceed
        (async () => {
          let apiUrl = '/api';
          try {
            const cfg = await configService.getConfig();
            apiUrl = cfg.api_url;
          } catch (e) {
            if (typeof window !== 'undefined') {
              const protocol = window.location.protocol;
              const host = window.location.host;
              apiUrl = `${protocol}//${host}/api`;
            }
          }
          const targetUrl = `${apiUrl}/media/upload`;
          if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
            console.log('📤 [useMediaUpload] Uploading to:', targetUrl);
          }
          xhr.open('POST', targetUrl);
          xhr.send(formData);
        })();
      });

      updateUpload(id, {
        status: 'completed',
        progress: 100,
        result,
        abortController: undefined,
      });

  // (export flow removed for explorer direct uploads—handled above)

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      updateUpload(id, {
        status: 'error',
        error: errorMessage,
        abortController: undefined,
      });
      throw error;
    }
  }, [updateUpload]);

  const upload = useCallback(async (files: FileList | File[]): Promise<UploadResult[]> => {
    const fileArray = Array.from(files);
  const uploadItems = fileArray.map(f => createUploadItem(f));

    // Add to queue
    setUploads(prev => [...prev, ...uploadItems]);

    // Upload all files
    const results: UploadResult[] = [];
    const errors: string[] = [];

    for (const uploadItem of uploadItems) {
      try {
        const result = await uploadSingleFile(uploadItem);
        results.push(result);
      } catch (error) {
        errors.push(error instanceof Error ? error.message : 'Upload failed');
      }
    }

    // If all failed, throw error
    if (results.length === 0 && errors.length > 0) {
      throw new Error(errors[0]);
    }

    return results;
  }, [createUploadItem, uploadSingleFile]);

  const cancel = useCallback((id: string) => {
    const upload = uploads.find(u => u.id === id);
    if (upload?.abortController) {
      upload.abortController.abort();
    }
    updateUpload(id, {
      status: 'error',
      error: 'Cancelled by user',
      abortController: undefined,
    });
  }, [uploads, updateUpload]);

  const retry = useCallback(async (id: string) => {
    const upload = uploads.find(u => u.id === id);
    if (!upload || upload.status !== 'error') return;

    try {
      await uploadSingleFile(upload);
    } catch (error) {
      // Error handling is done in uploadSingleFile
    }
  }, [uploads, uploadSingleFile]);

  const clear = useCallback(() => {
    // Cancel any ongoing uploads
    uploads.forEach(upload => {
      if (upload.abortController) {
        upload.abortController.abort();
      }
    });
    setUploads([]);
  }, [uploads]);

  const addFiles = useCallback((files: FileList | File[], options?: { context?: 'chat' | 'explorer'; destPath?: string }) => {
    const fileArray = Array.from(files);
    const uploadItems = fileArray.map(f => createUploadItem(f, options));
    setUploads(prev => [...prev, ...uploadItems]);
  }, [createUploadItem]);

  // Auto-start effect: whenever new pending uploads exist and none uploading
  React.useEffect(() => {
    if (!autoStart) return;
    const next = uploads.find(u => u.status === 'pending');
    const active = uploads.some(u => u.status === 'uploading');
    if (next && !active) {
      uploadSingleFile(next).catch(() => {/* error handled in uploadSingleFile */});
    }
  }, [uploads, autoStart, uploadSingleFile]);

  const removeFile = useCallback((id: string) => {
    setUploads(prev => {
      const u = prev.find(x => x.id === id);
      if (u?.abortController) u.abortController.abort();
      return prev.filter(upload => upload.id !== id);
    });
  }, []);

  const uploadAll = useCallback(async (): Promise<UploadResult[]> => {
    const pendingUploads = uploads.filter(upload => upload.status === 'pending');
    
    const results: UploadResult[] = [];
    const errors: string[] = [];

    for (const uploadItem of pendingUploads) {
      try {
        const result = await uploadSingleFile(uploadItem);
        results.push(result);
      } catch (error) {
        errors.push(error instanceof Error ? error.message : 'Upload failed');
      }
    }

    return results;
  }, [uploads, uploadSingleFile]);

  const clearCompleted = useCallback(() => {
    setUploads(prev => prev.filter(upload => 
      upload.status === 'uploading' || upload.status === 'pending'
    ));
  }, []);

  return {
    queue: uploads,              // Alias for UploadWidget compatibility
    uploads,
    isUploading,
    addFiles,
    uploadAll,
    upload,
    removeFile,
    cancel,
    retry,
    clear,
    clearCompleted,
  };
}

export default useMediaUpload;
