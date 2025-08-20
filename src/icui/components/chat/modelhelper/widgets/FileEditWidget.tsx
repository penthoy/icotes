/**
 * GPT-5 Specific FileEditWidget Component
 * 
 * Uses GPT-5 model helper for parsing file edit data with:
 * - GPT-5 specific data parsing
 * - Diff display (before/after)
 * - Syntax highlighting for file content
 * - Expand/collapse functionality
 * - File paths and modification timestamps
 * - ICUI theme integration
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { ChevronDown, ChevronRight, File, Clock, ExternalLink, Copy, Check, X } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../../../hooks/useTheme';
import { ToolCallData } from '../../ToolCallWidget';
import { gpt5Helper } from '../gpt5';

export interface GPT5FileEditWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

interface FileEditData {
  filePath: string;
  originalContent?: string;
  modifiedContent?: string;
  diff?: string;
  language?: string;
  timestamp?: string;
  operation?: 'create' | 'update' | 'delete' | 'read';
  lineNumbers?: {
    added: number[];
    removed: number[];
    modified: number[];
  };
  startLine?: number;
  endLine?: number;
}

// Helper function to detect language from file path
const getLanguageFromPath = (filePath: string): string => {
  const ext = filePath.split('.').pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'jsx',
    'ts': 'typescript',
    'tsx': 'tsx',
    'py': 'python',
    'rb': 'ruby',
    'php': 'php',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'cs': 'csharp',
    'go': 'go',
    'rs': 'rust',
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'fish': 'bash',
    'ps1': 'powershell',
    'sql': 'sql',
    'json': 'json',
    'xml': 'xml',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'sass',
    'less': 'less',
    'md': 'markdown',
    'yml': 'yaml',
    'yaml': 'yaml',
    'toml': 'toml',
    'ini': 'ini',
    'cfg': 'ini',
    'conf': 'ini'
  };
  return languageMap[ext || ''] || 'text';
};

const GPT5FileEditWidget: React.FC<GPT5FileEditWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false,
  onRetry
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [activeTab, setActiveTab] = useState<'diff' | 'before' | 'after'>('diff');
  const [copiedState, setCopiedState] = useState<string | null>(null);
  const { isDark } = useTheme();

  // Parse file edit data using GPT-5 helper
  const fileEditData = useMemo((): FileEditData => {
    const data = gpt5Helper.parseFileEditData(toolCall);
    return {
      ...data,
      language: getLanguageFromPath(data.filePath || '')
    };
  }, [toolCall]);

  // Auto-expand on error or when there's interesting content
  useEffect(() => {
    if (toolCall.status === 'error' || fileEditData.diff || fileEditData.originalContent) {
      setIsExpanded(true);
    }
  }, [toolCall.status, fileEditData.diff, fileEditData.originalContent]);

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  // Handle copy functionality
  const handleCopy = useCallback(async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedState(type);
      setTimeout(() => setCopiedState(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  // Handle retry action
  const handleRetry = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (onRetry) {
      onRetry(toolCall.id);
    }
  }, [onRetry, toolCall.id]);

  // Get status color and icon
  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      case 'running': return 'text-blue-500';
      default: return 'text-yellow-500';
    }
  };

  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'success': return '✅';
      case 'error': return '❌';
      case 'running': return '🔄';
      default: return '⏳';
    }
  };

  const getOperationIcon = () => {
    switch (fileEditData.operation) {
      case 'create': return '📝';
      case 'update': return '✏️';
      case 'delete': return '🗑️';
      case 'read': return '👁️';
      default: return '📄';
    }
  };

  const formatFilePath = (path: string) => 
    path.length > 50 ? `...${path.slice(-47)}` : path;

  return (
    <div 
      className={`border rounded-lg overflow-hidden ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)'
      }}
    >
      {/* Header */}
      <div 
        className={`flex items-center justify-between p-3 ${expandable ? 'cursor-pointer hover:bg-opacity-80' : ''}`}
        onClick={handleToggleExpansion}
        style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {expandable && (
            <div className="flex-shrink-0">
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
          )}
          
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg">{getOperationIcon()}</span>
            <File size={16} className="flex-shrink-0" />
            <div className="min-w-0">
              <div 
                className="font-mono text-sm truncate"
                style={{ color: 'var(--icui-text-primary)' }}
                title={fileEditData.filePath}
              >
                {formatFilePath(fileEditData.filePath)}
              </div>
              <div 
                className="text-xs opacity-70"
                style={{ color: 'var(--icui-text-secondary)' }}
              >
                {fileEditData.operation} • {fileEditData.language}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {fileEditData.timestamp && (
            <div 
              className="flex items-center gap-1 text-xs opacity-70"
              style={{ color: 'var(--icui-text-secondary)' }}
            >
              <Clock size={12} />
              <span>{fileEditData.timestamp}</span>
            </div>
          )}
          
          <div className={`flex items-center gap-1 text-sm ${getStatusColor()}`}>
            <span>{getStatusIcon()}</span>
            <span className="capitalize">{toolCall.status}</span>
          </div>

          {toolCall.status === 'error' && onRetry && (
            <button
              onClick={handleRetry}
              className="px-2 py-1 text-xs rounded border hover:bg-opacity-80 transition-colors"
              style={{
                backgroundColor: 'var(--icui-bg-primary)',
                borderColor: 'var(--icui-border-subtle)',
                color: 'var(--icui-text-primary)'
              }}
            >
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t" style={{ borderColor: 'var(--icui-border-subtle)' }}>
          {/* Error Display */}
          {toolCall.error && (
            <div 
              className="p-3 border-b"
              style={{ 
                backgroundColor: 'var(--icui-bg-error)',
                borderColor: 'var(--icui-border-subtle)'
              }}
            >
              <div className="flex items-start gap-2">
                <X size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-red-600 mb-1">Error</div>
                  <pre 
                    className="text-sm whitespace-pre-wrap font-mono"
                    style={{ color: 'var(--icui-text-primary)' }}
                  >
                    {toolCall.error}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Content Tabs */}
          {(fileEditData.diff || fileEditData.originalContent || fileEditData.modifiedContent) && (
            <>
              <div 
                className="flex border-b"
                style={{ borderColor: 'var(--icui-border-subtle)' }}
              >
                {fileEditData.diff && (
                  <button
                    onClick={() => setActiveTab('diff')}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'diff' 
                        ? 'border-blue-500 text-blue-600' 
                        : 'border-transparent hover:border-gray-300'
                    }`}
                    style={{ color: activeTab === 'diff' ? 'var(--icui-accent)' : 'var(--icui-text-secondary)' }}
                  >
                    Diff
                  </button>
                )}
                {fileEditData.originalContent && (
                  <button
                    onClick={() => setActiveTab('before')}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'before' 
                        ? 'border-blue-500 text-blue-600' 
                        : 'border-transparent hover:border-gray-300'
                    }`}
                    style={{ color: activeTab === 'before' ? 'var(--icui-accent)' : 'var(--icui-text-secondary)' }}
                  >
                    Before
                  </button>
                )}
                {fileEditData.modifiedContent && (
                  <button
                    onClick={() => setActiveTab('after')}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'after' 
                        ? 'border-blue-500 text-blue-600' 
                        : 'border-transparent hover:border-gray-300'
                    }`}
                    style={{ color: activeTab === 'after' ? 'var(--icui-accent)' : 'var(--icui-text-secondary)' }}
                  >
                    After
                  </button>
                )}
              </div>

              {/* Tab Content */}
              <div className="relative">
                {/* Copy Button */}
                <button
                  onClick={() => {
                    const content = activeTab === 'diff' ? fileEditData.diff :
                                   activeTab === 'before' ? fileEditData.originalContent :
                                   fileEditData.modifiedContent;
                    if (content) handleCopy(content, activeTab);
                  }}
                  className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                  style={{
                    backgroundColor: 'var(--icui-bg-secondary)',
                    borderColor: 'var(--icui-border-subtle)',
                    color: 'var(--icui-text-secondary)'
                  }}
                  title={copiedState === activeTab ? 'Copied!' : 'Copy content'}
                >
                  {copiedState === activeTab ? (
                    <>
                      <Check size={12} />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>

                {/* Diff Tab */}
                {activeTab === 'diff' && fileEditData.diff && (
                  <SyntaxHighlighter
                    language="diff"
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {fileEditData.diff}
                  </SyntaxHighlighter>
                )}

                {/* Before Tab */}
                {activeTab === 'before' && fileEditData.originalContent && (
                  <SyntaxHighlighter
                    language={fileEditData.language}
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {fileEditData.originalContent}
                  </SyntaxHighlighter>
                )}

                {/* After Tab */}
                {activeTab === 'after' && fileEditData.modifiedContent && (
                  <SyntaxHighlighter
                    language={fileEditData.language}
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {fileEditData.modifiedContent}
                  </SyntaxHighlighter>
                )}
              </div>
            </>
          )}

          {/* File Info */}
          {(fileEditData.startLine || fileEditData.endLine) && (
            <div 
              className="p-3 border-t text-xs"
              style={{ 
                backgroundColor: 'var(--icui-bg-tertiary)',
                borderColor: 'var(--icui-border-subtle)',
                color: 'var(--icui-text-secondary)'
              }}
            >
              <div className="flex items-center gap-4">
                {fileEditData.startLine && (
                  <span>Start Line: {fileEditData.startLine}</span>
                )}
                {fileEditData.endLine && (
                  <span>End Line: {fileEditData.endLine}</span>
                )}
                {fileEditData.startLine && fileEditData.endLine && (
                  <span>Lines: {fileEditData.endLine - fileEditData.startLine + 1}</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GPT5FileEditWidget; 