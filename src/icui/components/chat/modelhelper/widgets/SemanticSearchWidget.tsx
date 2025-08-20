/**
 * GPT-5 Specific SemanticSearchWidget Component
 * 
 * Uses GPT-5 model helper for parsing semantic search data with:
 * - GPT-5 specific data parsing
 * - Search results display with file paths and snippets
 * - Syntax highlighting for code snippets
 * - Expandable results with copy functionality
 * - ICUI theme integration
 */

import React, { useState, useCallback, useMemo } from 'react';
import { ChevronDown, ChevronRight, Search, File, Copy, Check, ExternalLink } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../../../hooks/useTheme';
import { ToolCallData } from '../../ToolCallWidget';
import { gpt5Helper } from '../gpt5';

export interface GPT5SemanticSearchWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
}

interface SearchResult {
  file: string;
  line?: number;
  snippet: string;
}

interface SearchData {
  query: string;
  scope: string;
  fileTypes: string[];
  results: SearchResult[];
  resultCount: number;
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
    'sql': 'sql',
    'json': 'json',
    'xml': 'xml',
    'html': 'html',
    'css': 'css',
    'md': 'markdown',
    'yml': 'yaml',
    'yaml': 'yaml'
  };
  return languageMap[ext || ''] || 'text';
};

const GPT5SemanticSearchWidget: React.FC<GPT5SemanticSearchWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const { isDark } = useTheme();

  // Parse search data using GPT-5 helper
  const searchData = useMemo((): SearchData => {
    return gpt5Helper.parseSemanticSearchData(toolCall);
  }, [toolCall]);

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  // Handle copy functionality
  const handleCopy = useCallback(async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedStates(prev => ({ ...prev, [id]: true }));
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [id]: false }));
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

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

  // Format file path for display
  const formatFilePath = (path: string) =>
    path.length > 40 ? `...${path.slice(-37)}` : path;

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
            <span className="text-lg">🔍</span>
            <Search size={16} className="flex-shrink-0" />
            <div className="min-w-0">
              <div 
                className="font-medium text-sm"
                style={{ color: 'var(--icui-text-primary)' }}
              >
                Semantic Search
              </div>
              <div 
                className="text-xs opacity-70 truncate"
                style={{ color: 'var(--icui-text-secondary)' }}
                title={searchData.query}
              >
                "{searchData.query}"
                {searchData.scope && ` in ${searchData.scope}`}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {searchData.resultCount > 0 && (
            <div 
              className="px-2 py-1 rounded text-xs font-medium"
              style={{
                backgroundColor: 'var(--icui-bg-success)',
                color: 'var(--icui-text-success)'
              }}
            >
              {searchData.resultCount} result{searchData.resultCount !== 1 ? 's' : ''}
            </div>
          )}
          
          <div className={`flex items-center gap-1 text-sm ${getStatusColor()}`}>
            <span>{getStatusIcon()}</span>
            <span className="capitalize">{toolCall.status}</span>
          </div>
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
                <div className="text-red-500">❌</div>
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-red-600 mb-1">Search Error</div>
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

          {/* Search Info */}
          <div 
            className="p-3 border-b text-sm"
            style={{ 
              backgroundColor: 'var(--icui-bg-tertiary)',
              borderColor: 'var(--icui-border-subtle)',
              color: 'var(--icui-text-primary)'
            }}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <div>
                <span className="font-medium">Query:</span>{' '}
                <span className="font-mono">{searchData.query}</span>
              </div>
              {searchData.scope && (
                <div>
                  <span className="font-medium">Scope:</span>{' '}
                  <span className="font-mono">{searchData.scope}</span>
                </div>
              )}
              {searchData.fileTypes.length > 0 && (
                <div className="md:col-span-2">
                  <span className="font-medium">File Types:</span>{' '}
                  <span className="font-mono">{searchData.fileTypes.join(', ')}</span>
                </div>
              )}
            </div>
          </div>

          {/* Results */}
          {searchData.results.length > 0 ? (
            <div className="divide-y" style={{ borderColor: 'var(--icui-border-subtle)' }}>
              {searchData.results.map((result, index) => {
                const resultId = `result-${index}`;
                const isCopied = copiedStates[resultId];
                const language = getLanguageFromPath(result.file);

                return (
                  <div key={index} className="p-4">
                    {/* File Header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <File size={16} className="flex-shrink-0" />
                        <div 
                          className="font-mono text-sm truncate"
                          style={{ color: 'var(--icui-text-primary)' }}
                          title={result.file}
                        >
                          {formatFilePath(result.file)}
                        </div>
                        {result.line && (
                          <div 
                            className="text-xs px-2 py-1 rounded"
                            style={{
                              backgroundColor: 'var(--icui-bg-tertiary)',
                              color: 'var(--icui-text-secondary)'
                            }}
                          >
                            Line {result.line}
                          </div>
                        )}
                      </div>
                      
                      <button
                        onClick={() => handleCopy(result.snippet, resultId)}
                        className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                        style={{
                          backgroundColor: 'var(--icui-bg-secondary)',
                          borderColor: 'var(--icui-border-subtle)',
                          color: 'var(--icui-text-secondary)'
                        }}
                        title={isCopied ? 'Copied!' : 'Copy snippet'}
                      >
                        {isCopied ? (
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
                    </div>

                    {/* Code Snippet */}
                    {result.snippet && (
                      <div className="relative">
                        <SyntaxHighlighter
                          language={language}
                          style={isDark ? oneDark : oneLight}
                          customStyle={{
                            margin: 0,
                            fontSize: '0.875rem',
                            lineHeight: '1.5',
                            borderRadius: '0.375rem'
                          }}
                          showLineNumbers={false}
                          wrapLines={true}
                        >
                          {result.snippet}
                        </SyntaxHighlighter>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : toolCall.status === 'success' ? (
            <div 
              className="p-6 text-center"
              style={{ color: 'var(--icui-text-secondary)' }}
            >
              <Search size={48} className="mx-auto mb-2 opacity-50" />
              <div className="text-sm">No results found for your search query.</div>
              <div className="text-xs mt-1 opacity-70">
                Try adjusting your search terms or scope.
              </div>
            </div>
          ) : toolCall.status === 'running' ? (
            <div 
              className="p-6 text-center"
              style={{ color: 'var(--icui-text-secondary)' }}
            >
              <div className="animate-spin mb-2 mx-auto">🔄</div>
              <div className="text-sm">Searching...</div>
            </div>
          ) : null}

          {/* Summary Footer */}
          {searchData.results.length > 0 && (
            <div 
              className="p-3 border-t text-xs"
              style={{ 
                backgroundColor: 'var(--icui-bg-tertiary)',
                borderColor: 'var(--icui-border-subtle)',
                color: 'var(--icui-text-secondary)'
              }}
            >
              <div className="flex items-center justify-between">
                <span>
                  Found {searchData.resultCount} result{searchData.resultCount !== 1 ? 's' : ''}
                </span>
                {toolCall.startTime && toolCall.endTime && (
                  <span>
                    Search completed in {toolCall.endTime.getTime() - toolCall.startTime.getTime()}ms
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GPT5SemanticSearchWidget; 