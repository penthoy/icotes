/**
 * FileEditWidget Component
 * 
 * Displays file edit operations from tool calls with:
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
import { useTheme } from '../../../hooks/useTheme';
import { ToolCallData } from '../ToolCallWidget';
import { getActiveModelHelper } from '../modelhelper';
import { formatFilePath } from '../../../utils/pathUtils';

export interface FileEditWidgetProps {
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
  operation?: 'create' | 'update' | 'delete';
  lineNumbers?: {
    added: number[];
    removed: number[];
    modified: number[];
  };
  startLine?: number;
  endLine?: number;
  totalLines?: number;
  totalSize?: number;
}

const FileEditWidget: React.FC<FileEditWidgetProps> = ({
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

  // Parse file edit data using active model helper
  const fileEditData = useMemo((): FileEditData => {
    const helper = getActiveModelHelper();
    const data = helper.parseFileEditData(toolCall);
    return {
      ...data,
      language: getLanguageFromPath(data.filePath || '')
    };
  }, [toolCall]);

  // Get programming language from file path
  function getLanguageFromPath(filePath: string): string {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const languageMap: { [key: string]: string } = {
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'py': 'python',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'json': 'json',
      'xml': 'xml',
      'yaml': 'yaml',
      'yml': 'yaml',
      'md': 'markdown',
      'sh': 'bash',
      'sql': 'sql'
    };
    return languageMap[ext || ''] || 'text';
  }

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  // Handle retry action
  const handleRetry = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (onRetry) {
      onRetry(toolCall.id);
    }
  }, [onRetry, toolCall.id]);

  // Copy content to clipboard
  const handleCopy = useCallback(async (content: string, type: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedState(type);
      setTimeout(() => setCopiedState(null), 2000);
    } catch (error) {
      console.error('Failed to copy content:', error);
    }
  }, []);

  // Generate simple diff view
  const generateDiffView = useCallback(() => {
    if (fileEditData.diff) {
      return fileEditData.diff;
    }

    if (!fileEditData.originalContent || !fileEditData.modifiedContent) {
      return fileEditData.modifiedContent || 'No content available';
    }

    // Simple line-by-line diff
    const originalLines = fileEditData.originalContent.split('\n');
    const modifiedLines = fileEditData.modifiedContent.split('\n');
    const maxLines = Math.max(originalLines.length, modifiedLines.length);
    
    let diffContent = '';
    for (let i = 0; i < maxLines; i++) {
      const originalLine = originalLines[i] || '';
      const modifiedLine = modifiedLines[i] || '';
      
      if (originalLine === modifiedLine) {
        diffContent += `  ${modifiedLine}\n`;
      } else if (originalLine && !modifiedLine) {
        diffContent += `- ${originalLine}\n`;
      } else if (!originalLine && modifiedLine) {
        diffContent += `+ ${modifiedLine}\n`;
      } else {
        diffContent += `- ${originalLine}\n`;
        diffContent += `+ ${modifiedLine}\n`;
      }
    }
    
    return diffContent;
  }, [fileEditData]);

  // Get operation icon and color
  const getOperationIcon = () => {
    switch (fileEditData.operation) {
      case 'create':
        return <span className="text-green-500">+</span>;
      case 'delete':
        return <span className="text-red-500">-</span>;
      case 'update':
      default:
        return <span className="text-blue-500">~</span>;
    }
  };

  // Get status color
  const getStatusColor = () => {
    switch (toolCall.status) {
      case 'success':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      case 'running':
        return 'text-blue-500';
      default:
        return 'text-yellow-500';
    }
  };

  const availableTabs = useMemo(() => {
    const originalToolName = toolCall.metadata?.originalToolName || toolCall.toolName;
    
    // For read_file operations, don't show tabs - just show content
    if (originalToolName === 'read_file') {
      return [];
    }
    
    // For create_file operations, don't show tabs - just show summary
    if (originalToolName === 'create_file') {
      return [];
    }
    
    const tabs: Array<'diff' | 'before' | 'after'> = [];
    
    if (fileEditData.diff) {
      tabs.push('diff');
    }
    if (fileEditData.originalContent) {
      tabs.push('before');
    }
    if (fileEditData.modifiedContent) {
      tabs.push('after');
    }
    
    // If no tabs available, default to 'after' for update operations only
    if (tabs.length === 0 && originalToolName === 'replace_string_in_file') {
      tabs.push('after');
    }
    
    return tabs;
  }, [fileEditData, toolCall.metadata?.originalToolName]);

  // Ensure activeTab is valid
  useEffect(() => {
    if (availableTabs.length > 0 && !availableTabs.includes(activeTab)) {
      setActiveTab(availableTabs[0]);
    }
  }, [availableTabs, activeTab]);

  const statusInfo = useMemo(() => {
    switch (toolCall.status) {
      case 'success':
        return { icon: <Check size={12} />, color: 'text-green-500' };
      case 'error':
        return { icon: <X size={12} />, color: 'text-red-500' };
      case 'running':
        return { icon: <Clock size={12} />, color: 'text-blue-500' };
      default:
        return { icon: <File size={12} />, color: 'text-yellow-500' };
    }
  }, [toolCall.status]);

  const originalToolName = toolCall.metadata?.originalToolName || toolCall.toolName;
  const isReadOperation = originalToolName === 'read_file';
  const isCreateOperation = originalToolName === 'create_file';
  
  // Content is expandable if there are tabs to show (diff/before/after) or if this is a read operation
  const shouldShowExpandableContent = useMemo(() => {
    return availableTabs.length > 0 || isReadOperation;
  }, [availableTabs.length, isReadOperation]);

  return (
    <div className={`icui-widget ${className}`}>
      {/* Header */}
      <div className={`icui-widget__header ${shouldShowExpandableContent ? 'icui--clickable' : ''}`} onClick={shouldShowExpandableContent ? handleToggleExpansion : undefined}>
        {/* Expansion indicator */}
        {shouldShowExpandableContent && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-500" />
            ) : (
              <ChevronRight size={14} className="text-gray-500" />
            )}
          </div>
        )}

        {/* Tool name chip */}
        <span className="icui-chip">{toolCall.metadata?.originalToolName || toolCall.toolName}</span>
        {toolCall.status === 'running' && <span className="icui-spinner" aria-label="running" />}

        {/* Status icon */}
        <div className={`flex-shrink-0 ${statusInfo.color}`}>
          {statusInfo.icon}
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="icui-widget__title">{formatFilePath(fileEditData.filePath)}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${statusInfo.color}`}>
              {isCreateOperation ? 'CREATE' : String(fileEditData.operation || 'update').toUpperCase()}
            </span>
          </div>
          {fileEditData.timestamp && (
            <div className="icui-widget__meta mt-1">
              {fileEditData.timestamp}
            </div>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && shouldShowExpandableContent && (
        <div>
          {/* Show error information if failed */}
          {toolCall.status === 'error' && toolCall.error && (
            <div className="icui-widget__section">
              <div className="icui-widget__error">
                <div className="font-medium mb-2">Error Details:</div>
                <div className="text-sm mb-2">
                  <strong>Operation:</strong> {originalToolName}
                </div>
                <div className="text-sm mb-2">
                  <strong>Target:</strong> {fileEditData.filePath}
                </div>
                <div className="text-sm">
                  <strong>Error:</strong> {toolCall.error}
                </div>
              </div>
            </div>
          )}

          {/* For read operations, show file path and line range, plus content preview */}
          {isReadOperation && toolCall.status === 'success' && (
            <div className="icui-widget__section">
              <div className="text-sm icui-widget__meta mb-2">
                <strong>File Path:</strong> {fileEditData.filePath}
              </div>
              {(fileEditData.startLine || fileEditData.endLine) && (
                <div className="text-sm icui-widget__meta mb-2">
                  <strong>Lines:</strong> {fileEditData.startLine || 1} - {fileEditData.endLine || 'end'}
                </div>
              )}
              {/* Show file statistics if available */}
              {(fileEditData.totalLines || fileEditData.totalSize) && (
                <div className="text-sm icui-widget__meta mb-2">
                  <strong>File Size:</strong> 
                  {fileEditData.totalLines && ` ${fileEditData.totalLines} lines`}
                  {fileEditData.totalSize && ` • ${Math.round(fileEditData.totalSize / 1024)}KB`}
                </div>
              )}
              {/* Show content preview if available */}
              {fileEditData.modifiedContent && (
                <div className="mt-3">
                  <div className="text-sm icui-widget__meta mb-2">
                    <strong>Content Preview:</strong>
                    {fileEditData.totalLines && fileEditData.totalLines > 10 && (
                      <span className="ml-2 text-xs opacity-75">
                        (showing first 10 of {fileEditData.totalLines} lines)
                      </span>
                    )}
                  </div>
                  <SyntaxHighlighter
                    language={fileEditData.language}
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      borderRadius: '6px',
                      background: 'var(--icui-bg-primary)',
                      border: '1px solid var(--icui-border-subtle)',
                      fontSize: '0.75rem',
                      lineHeight: '1.4',
                      maxHeight: '200px',
                      overflow: 'auto'
                    }}
                    showLineNumbers={true}
                    startingLineNumber={fileEditData.startLine || 1}
                  >
                    {fileEditData.modifiedContent}
                  </SyntaxHighlighter>
                </div>
              )}
            </div>
          )}

          {/* For create/update operations, show tabs if available */}
          {!isReadOperation && !isCreateOperation && availableTabs.length > 0 && (
            <>
              {/* Tabs */}
              <div className="icui-widget__tabs">
                {availableTabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`icui-widget__tab ${activeTab === tab ? 'icui--active' : ''}`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {/* Content */}
              <div className="icui-widget__section">
                {activeTab === 'diff' && fileEditData.diff && (
                  <SyntaxHighlighter
                    language="diff"
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      borderRadius: '6px',
                      background: 'var(--icui-bg-primary)',
                      border: '1px solid var(--icui-border-subtle)',
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                  >
                    {fileEditData.diff}
                  </SyntaxHighlighter>
                )}

                {activeTab === 'before' && fileEditData.originalContent && (
                  <SyntaxHighlighter
                    language={fileEditData.language}
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      borderRadius: '6px',
                      background: 'var(--icui-bg-primary)',
                      border: '1px solid var(--icui-border-subtle)',
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                  >
                    {fileEditData.originalContent}
                  </SyntaxHighlighter>
                )}

                {activeTab === 'after' && (
                  <div>
                    {fileEditData.modifiedContent ? (
                      <SyntaxHighlighter
                        language={fileEditData.language}
                        style={isDark ? oneDark : oneLight}
                        customStyle={{
                          margin: 0,
                          borderRadius: '6px',
                          background: 'var(--icui-bg-primary)',
                          border: '1px solid var(--icui-border-subtle)',
                          fontSize: '0.875rem',
                          lineHeight: '1.5'
                        }}
                        showLineNumbers={true}
                      >
                        {fileEditData.modifiedContent}
                      </SyntaxHighlighter>
                    ) : (
                      <div className="text-center py-8 text-gray-500 border border-dashed" style={{ borderColor: '#e5e7eb' }}>
                        No content available
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default FileEditWidget; 