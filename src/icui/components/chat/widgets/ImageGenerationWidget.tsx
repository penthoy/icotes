/**
 * ImageGenerationWidget Component
 * 
 * Displays AI-generated images from tool calls with:
 * - Image preview with loading states
 * - Generation parameters display
 * - Download and copy functionality
 * - Error handling
 * - Expandable details
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Image, ChevronDown, ChevronRight, CheckCircle, XCircle, Clock, Download, Copy, Loader2 } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';
import { getActiveModelHelper } from '../modelhelper';

export interface ImageGenerationWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

interface GenerationData {
  prompt?: string;
  size?: string;
  style?: string;
  imageUrl?: string;
  imageData?: string; // base64 encoded image data (legacy or thumbnail)
  fullImageUrl?: string; // Streaming-optimized: URL for full-resolution image
  error?: string;
  timestamp?: number;
  status?: 'pending' | 'generating' | 'success' | 'error';
}

const ImageGenerationWidget: React.FC<ImageGenerationWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false,
  onRetry
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const [copied, setCopied] = useState(false);

  // Parse image generation data
  const generationData = useMemo<GenerationData>(() => {
    const helper = getActiveModelHelper();
    
    // Try to extract data from tool call
    let data: GenerationData = {
      status: toolCall.status as any || 'pending'
    };

    // Parse input parameters
    if (toolCall.input) {
      try {
        const input = typeof toolCall.input === 'string' 
          ? JSON.parse(toolCall.input) 
          : toolCall.input;
        data.prompt = input.prompt || '';
        
        // Check for width/height parameters first (Phase 7 resolution control)
        if (input.width || input.height) {
          const w = input.width || 'auto';
          const h = input.height || 'auto';
          data.size = `${w}x${h}`;
        } else {
          // Fall back to size parameter or default
          data.size = input.size || '1024x1024';
        }
        
        data.style = input.style || 'natural';
      } catch (e) {
        console.warn('Failed to parse image generation input:', e);
      }
    }

    // Parse output (image URL or data)
    if (toolCall.output && toolCall.status === 'success') {
      try {
        let output;
        
        if (typeof toolCall.output === 'string') {
          // Try to extract JSON from formatted output like "✅ **Success**: {...}"
          const jsonMatch = toolCall.output.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            console.log('[ImageWidget] Extracting JSON from formatted output');
            output = JSON.parse(jsonMatch[0]);
          } else {
            console.warn('[ImageWidget] No JSON found in output:', toolCall.output.substring(0, 100));
            output = {};
          }
        } else {
          output = toolCall.output;
        }
        
        console.log('[ImageWidget] Parsed output:', {
          hasImageReference: !!output.imageReference,
          hasImageData: !!output.imageData,
          hasImageUrl: !!output.imageUrl,
          hasFullImageUrl: !!output.fullImageUrl,
          size: output.size
        });
        
        // Override size from output if available (actual dimensions)
        if (output.size) {
          data.size = output.size;
        }
        
        // Performance optimized: Use streaming-optimized image endpoints
        if (output.imageReference) {
          const ref = output.imageReference;
          
          // Priority 1: Use embedded imageData (thumbnail) for instant preview
          if (output.imageData) {
            data.imageData = output.imageData;
          } else if (ref.thumbnail_base64) {
            data.imageData = ref.thumbnail_base64;
          }
          
          // Store URLs for agent editing and downloads
          data.imageUrl = output.imageUrl;  // file:// URL for agent editing
          data.fullImageUrl = output.fullImageUrl;  // API endpoint for downloads
          
          console.log('[ImageWidget] Using streaming-optimized format:', {
            imageUrl: data.imageUrl,
            fullImageUrl: data.fullImageUrl,
            hasThumbnail: !!data.imageData
          });
          
          // Store metadata
          data.timestamp = ref.timestamp ? ref.timestamp * 1000 : Date.now();
          if (ref.prompt) data.prompt = ref.prompt;
        } else {
          // Legacy format: direct imageUrl/imageData (pre-optimization)
          data.imageUrl = output.url || output.imageUrl || output.image_url;
          data.imageData = output.data || output.imageData || output.image_data;
          data.timestamp = output.timestamp || Date.now();
          
          console.log('[ImageWidget] Using legacy format:', {
            imageUrl: data.imageUrl,
            hasImageData: !!data.imageData
          });
        }
        
        data.status = 'success';
          // Fallback: if prompt not set from input, try output
          if (!data.prompt && (output.prompt || output.description)) {
            data.prompt = output.prompt || output.description;
          }
      } catch (e) {
        console.error('[ImageWidget] Failed to parse image generation output:', e);
        console.error('[ImageWidget] Raw output:', typeof toolCall.output === 'string' ? toolCall.output.substring(0, 200) : toolCall.output);
      }
    }

    // Parse error if present
    if (toolCall.error) {
      data.error = typeof toolCall.error === 'string' 
        ? toolCall.error 
        : JSON.stringify(toolCall.error);
      data.status = 'error';
    }

    return data;
  }, [toolCall]);

  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [generationData.imageData, generationData.imageUrl, toolCall.id]);

  useEffect(() => {
    setCopied(false);
  }, [toolCall.id, generationData.imageUrl, generationData.imageData]);

  // Get status icon and color
  const { icon: StatusIcon, color, bgColor } = useMemo(() => {
    switch (toolCall.status) {
      case 'success':
        return { 
          icon: CheckCircle, 
          color: 'text-green-600 dark:text-green-400', 
          bgColor: 'bg-green-50 dark:bg-green-900/20' 
        };
      case 'error':
        return { 
          icon: XCircle, 
          color: 'text-red-600 dark:text-red-400', 
          bgColor: 'bg-red-50 dark:bg-red-900/20' 
        };
      case 'running':
        return { 
          icon: Loader2, 
          color: 'text-blue-600 dark:text-blue-400', 
          bgColor: 'bg-blue-50 dark:bg-blue-900/20' 
        };
      default:
        return { 
          icon: Clock, 
          color: 'text-gray-600 dark:text-gray-400', 
          bgColor: 'bg-gray-50 dark:bg-gray-900/20' 
        };
    }
  }, [toolCall.status]);

  // Handle image download
  const handleDownload = useCallback(() => {
    // Use fullImageUrl for download to get high-quality version
    const downloadUrl = (generationData as any).fullImageUrl || generationData.imageUrl;
    
    if (downloadUrl) {
      const link = document.createElement('a');
      // Convert file:// URLs to API endpoints
      if (downloadUrl.startsWith('file://')) {
        const filePath = downloadUrl.replace('file://', '');
        link.href = `/api/files/raw?path=${encodeURIComponent(filePath)}`;
      } else {
        link.href = downloadUrl;
      }
      link.download = `generated-image-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else if (generationData.imageData) {
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${generationData.imageData}`;
      link.download = `generated-image-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [generationData]);

  // Handle copy image URL
  const handleCopyUrl = useCallback(async () => {
    if (generationData.imageUrl) {
      try {
        await navigator.clipboard.writeText(generationData.imageUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('Failed to copy URL:', err);
      }
    }
  }, [generationData.imageUrl]);

  // Get display image source
  const imageSrc = useMemo(() => {
    // Priority 1: Use fullImageUrl for high-quality display (streaming-optimized format)
    if ((generationData as any).fullImageUrl) {
      return (generationData as any).fullImageUrl;
    }
    
    // Priority 2: Convert file:// URLs to API endpoints for full image
    if (generationData.imageUrl) {
      if (generationData.imageUrl.startsWith('file://')) {
        const filePath = generationData.imageUrl.replace('file://', '');
        return `/api/files/raw?path=${encodeURIComponent(filePath)}`;
      }
      return generationData.imageUrl;
    }
    
    // Priority 3: Fallback to embedded thumbnail (fast but low quality)
    if (generationData.imageData) {
      return `data:image/png;base64,${generationData.imageData}`;
    }
    
    return null;
  }, [generationData]);

  return (
    <div className={`icui-widget border rounded-lg overflow-hidden ${className}`} 
         style={{ 
           backgroundColor: 'var(--icui-bg-secondary)', 
           borderColor: 'var(--icui-border)' 
         }}>
      {/* Header */}
      <div 
        className={`flex items-center justify-between p-3 ${expandable ? 'cursor-pointer' : ''} ${bgColor}`}
        onClick={() => expandable && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Image size={16} className="text-purple-600 dark:text-purple-400 flex-shrink-0" />
          <span className="font-medium text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>
            Image Generation
          </span>
          {toolCall.status === 'running' && (
            <Loader2 size={14} className="animate-spin text-blue-600 dark:text-blue-400 flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusIcon size={14} className={`${color} ${toolCall.status === 'running' ? 'animate-spin' : ''}`} />
          {expandable && (
            isExpanded ? 
              <ChevronDown size={16} className="text-gray-400" /> : 
              <ChevronRight size={16} className="text-gray-400" />
          )}
        </div>
      </div>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="p-4 space-y-3">
          {/* Prompt Display */}
          {generationData.prompt && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: 'var(--icui-text-secondary)' }}>
                Prompt:
              </div>
              <div className="text-sm p-2 rounded" 
                   style={{ 
                     backgroundColor: 'var(--icui-bg-tertiary)', 
                     color: 'var(--icui-text-primary)' 
                   }}>
                {generationData.prompt}
              </div>
            </div>
          )}

          {/* Generation Parameters */}
          {(generationData.size || generationData.style) && (
            <div className="flex gap-4 text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
              {generationData.size && (
                <div>
                  <span className="font-medium">Size:</span> {generationData.size}
                </div>
              )}
              {generationData.style && (
                <div>
                  <span className="font-medium">Style:</span> {generationData.style}
                </div>
              )}
            </div>
          )}

          {/* Generated Image */}
          {toolCall.status === 'success' && imageSrc && (
            <div className="space-y-2">
              <div className="text-xs font-medium" style={{ color: 'var(--icui-text-secondary)' }}>
                Generated Image:
              </div>
              <div className="relative group rounded-lg overflow-hidden" 
                   style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}>
                {!imageLoaded && !imageError && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Loader2 size={32} className="animate-spin text-gray-400" />
                  </div>
                )}
                {imageError ? (
                  <div className="p-8 text-center">
                    <XCircle size={48} className="mx-auto mb-2 text-red-400" />
                    <div className="text-sm text-red-600 dark:text-red-400">
                      Failed to load image
                    </div>
                  </div>
                ) : (
                  <img
                    src={imageSrc}
                    alt={generationData.prompt || 'Generated image'}
                    className="w-full h-auto"
                    onLoad={() => setImageLoaded(true)}
                    onError={() => setImageError(true)}
                  />
                )}
                
                {/* Image Controls Overlay */}
                {imageLoaded && !imageError && (
                  <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={handleDownload}
                      className="p-2 rounded bg-black/70 hover:bg-black/90 text-white transition-colors"
                      title="Download image"
                    >
                      <Download size={16} />
                    </button>
                    {generationData.imageUrl && (
                      <button
                        onClick={handleCopyUrl}
                        className="p-2 rounded bg-black/70 hover:bg-black/90 text-white transition-colors"
                        title={copied ? 'Copied!' : 'Copy URL'}
                      >
                        <Copy size={16} className={copied ? 'text-green-400' : ''} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Loading State */}
          {toolCall.status === 'running' && (
            <div className="flex items-center justify-center p-8 text-sm" 
                 style={{ color: 'var(--icui-text-secondary)' }}>
              <Loader2 size={20} className="animate-spin mr-2" />
              Generating image...
            </div>
          )}

          {/* Error Display */}
          {toolCall.status === 'error' && generationData.error && (
            <div className="p-3 rounded" style={{ backgroundColor: 'var(--icui-bg-error)' }}>
              <div className="text-sm font-medium text-red-600 dark:text-red-400 mb-1">
                Generation Failed
              </div>
              <div className="text-xs text-red-700 dark:text-red-300">
                {generationData.error}
              </div>
              {onRetry && (
                <button
                  onClick={() => onRetry(toolCall.id)}
                  className="mt-2 text-xs text-red-600 dark:text-red-400 hover:underline"
                >
                  Retry generation
                </button>
              )}
            </div>
          )}

          {/* Timestamp */}
          {generationData.timestamp && (
            <div className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
              Generated: {new Date(generationData.timestamp).toLocaleString()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageGenerationWidget;
