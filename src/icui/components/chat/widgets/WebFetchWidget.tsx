/**
 * WebFetchWidget Component
 * 
 * Displays web_fetch tool results with compact view and expandable iframe preview
 */

import React, { useState, useMemo } from 'react';
import { ExternalLink, Copy, Download, ChevronDown, ChevronUp, Maximize2, Minimize2, CheckCircle, XCircle, Clock, Globe } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';

export interface WebFetchWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
}

export const WebFetchWidget: React.FC<WebFetchWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showIframe, setShowIframe] = useState(false);
  const [iframeSize, setIframeSize] = useState<'small' | 'medium' | 'large'>('medium');
  const [activeTab, setActiveTab] = useState<'content' | 'links' | 'images' | 'structure'>('content');

  // Parse tool call data
  const { url, title, content, metadata, structure, links, images, was_truncated, truncation_reason } = useMemo(() => {
    const outputData = toolCall.output || {};
    const data = outputData.data || outputData;
    
    return {
      url: toolCall.input?.url || data.url || '',
      title: data.title || '',
      content: data.content || '',
      metadata: data.metadata || {},
      structure: data.structure || {},
      links: data.links || [],
      images: data.images || [],
      was_truncated: data.was_truncated || false,
      truncation_reason: data.truncation_reason || null
    };
  }, [toolCall]);

  const getStatusInfo = () => {
    switch (toolCall.status) {
      case 'success':
        return { icon: <CheckCircle size={12} />, color: 'text-green-500' };
      case 'error':
        return { icon: <XCircle size={12} />, color: 'text-red-500' };
      case 'running':
        return { icon: <Clock size={12} />, color: 'text-blue-500' };
      default:
        return { icon: <Globe size={12} />, color: 'text-yellow-500' };
    }
  };

  const statusInfo = getStatusInfo();
  const displayTitle = title || metadata?.title || 'Web Page';
  const isYouTube = metadata?.type === 'youtube_transcript';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
    } catch (err) {
      // Best-effort: clipboard may be blocked in some contexts
      console.error('Clipboard write failed:', err);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' });
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `${displayTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`;
    a.click();
    URL.revokeObjectURL(blobUrl);
  };

  const getSizeClass = () => {
    switch (iframeSize) {
      case 'small': return 'h-64';
      case 'medium': return 'h-96';
      case 'large': return 'h-[600px]';
    }
  };

  return (
    <div className={`border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800 shadow-sm my-2 ${className}`}>
      {/* Header */}
      <div className="bg-gray-50 dark:bg-gray-750 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={statusInfo.color}>
                {statusInfo.icon}
              </span>
              {isYouTube && (
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                  YouTube
                </span>
              )}
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                {displayTitle}
              </h3>
            </div>
            {url && (
              <a 
                href={url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 mt-1"
              >
                <ExternalLink className="w-3 h-3" />
                <span className="truncate">{url}</span>
              </a>
            )}
            {metadata?.description && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                {metadata.description}
              </p>
            )}
            {isYouTube && metadata?.language && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Language: {metadata.language}
                {metadata.is_generated && ' (auto-generated)'}
              </p>
            )}
            {metadata?.cache_hit && (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 mt-1">
                📦 Cached
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {content && (
              <>
                <button
                  onClick={handleCopy}
                  className="p-1.5 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="Copy content"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={handleDownload}
                  className="p-1.5 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  title="Download content"
                >
                  <Download className="w-4 h-4" />
                </button>
              </>
            )}
            {!isYouTube && url && (
              <button
                onClick={() => setShowIframe(!showIframe)}
                className="p-1.5 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                title={showIframe ? "Hide preview" : "Show preview"}
              >
                {showIframe ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>
            )}
            {expandable && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                title={isExpanded ? "Collapse" : "Expand"}
              >
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Iframe Preview (for non-YouTube URLs) */}
      {showIframe && !isYouTube && url && (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-2">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs text-gray-600 dark:text-gray-400">Live Preview</span>
            <div className="flex gap-1">
              <button
                onClick={() => setIframeSize('small')}
                className={`px-2 py-1 text-xs rounded ${
                  iframeSize === 'small' 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' 
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                Small
              </button>
              <button
                onClick={() => setIframeSize('medium')}
                className={`px-2 py-1 text-xs rounded ${
                  iframeSize === 'medium' 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' 
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                Medium
              </button>
              <button
                onClick={() => setIframeSize('large')}
                className={`px-2 py-1 text-xs rounded ${
                  iframeSize === 'large' 
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' 
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}
              >
                Large
              </button>
            </div>
          </div>
          <iframe
            src={url}
            className={`w-full ${getSizeClass()} border border-gray-300 dark:border-gray-600 rounded bg-white`}
            sandbox="allow-scripts allow-popups allow-forms"
            referrerPolicy="no-referrer"
            title={displayTitle}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Note: Some sites may block iframe embedding.
          </p>
        </div>
      )}

      {/* Error Display */}
      {toolCall.status === 'error' && toolCall.error && (
        <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <p className="text-sm text-red-800 dark:text-red-200">{toolCall.error}</p>
        </div>
      )}

      {/* Expanded Content */}
      {isExpanded && content && (
        <div className="p-4">
          {/* Tabs */}
          <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 mb-3">
            <button
              onClick={() => setActiveTab('content')}
              className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'content'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
            >
              Content
            </button>
            {structure?.toc && structure.toc.length > 0 && (
              <button
                onClick={() => setActiveTab('structure')}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'structure'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                Structure ({structure.toc.length})
              </button>
            )}
            {links && links.length > 0 && (
              <button
                onClick={() => setActiveTab('links')}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'links'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                Links ({links.length})
              </button>
            )}
            {images && images.length > 0 && (
              <button
                onClick={() => setActiveTab('images')}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'images'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                Images ({images.length})
              </button>
            )}
          </div>

          {/* Tab Content */}
          <div className="max-h-96 overflow-y-auto">
            {activeTab === 'content' && (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 font-mono bg-gray-50 dark:bg-gray-900 p-3 rounded">
                  {content}
                </pre>
                {was_truncated && (
                  <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 mt-2">
                    <p className="text-xs text-amber-800 dark:text-amber-200 font-medium">
                      ⚠️ Content Truncated
                    </p>
                    {truncation_reason && (
                      <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                        {truncation_reason}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'structure' && structure?.toc && (
              <div className="space-y-1">
                {structure.toc.map((item: any, index: number) => (
                  <div
                    key={index}
                    style={{ paddingLeft: `${(item.level - 1) * 16}px` }}
                    className="text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 p-1 rounded cursor-pointer"
                  >
                    <span className="text-gray-500 dark:text-gray-400 mr-2">
                      {item.level === 1 ? '📄' : item.level === 2 ? '📑' : '📋'}
                    </span>
                    {item.text}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'links' && links && (
              <div className="space-y-2">
                {links.map((link: any, index: number) => (
                  <div key={index} className="flex items-start gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                    <ExternalLink className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {link.text || 'Untitled Link'}
                      </p>
                      <a 
                        href={link.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate block"
                      >
                        {link.url}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'images' && images && (
              <div className="grid grid-cols-2 gap-3">
                {images.map((image: any, index: number) => (
                  <div key={index} className="border border-gray-200 dark:border-gray-700 rounded p-2">
                    <img 
                      src={image.url} 
                      alt={image.alt || 'Image'} 
                      className="w-full h-32 object-cover rounded mb-2"
                      loading="lazy"
                    />
                    <p className="text-xs text-gray-600 dark:text-gray-400 truncate" title={image.alt}>
                      {image.alt || 'No description'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Collapsed Preview */}
      {!isExpanded && content && (
        <div className="px-4 py-3">
          <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
            {content.substring(0, 200)}...
          </p>
          <div className="flex gap-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
            {structure?.toc && (
              <span>{structure.toc.length} sections</span>
            )}
            {links && links.length > 0 && (
              <span>{links.length} links</span>
            )}
            {images && images.length > 0 && (
              <span>{images.length} images</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default WebFetchWidget;
