/**
 * GPT-5 Specific CodeExecutionWidget Component
 * 
 * Uses GPT-5 model helper for parsing code execution data with:
 * - GPT-5 specific data parsing
 * - Code input/output with syntax highlighting
 * - Execution status and timing information
 * - Support for multiple output formats (text, JSON, HTML, etc.)
 * - Error handling and stack traces
 * - Copy functionality for code and results
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { ChevronDown, ChevronRight, Play, Clock, Copy, Check, AlertTriangle, Terminal } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../../../hooks/useTheme';
import { ToolCallData } from '../../ToolCallWidget';
import { gpt5Helper } from '../gpt5';

export interface GPT5CodeExecutionWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

interface CodeExecutionData {
  code: string;
  language: string;
  output?: string;
  error?: string;
  exitCode?: number;
  executionTime?: number;
  environment?: string;
  outputFormat?: 'text' | 'json' | 'html' | 'markdown';
  stackTrace?: string;
}

const GPT5CodeExecutionWidget: React.FC<GPT5CodeExecutionWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false,
  onRetry
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [activeTab, setActiveTab] = useState<'code' | 'output' | 'error'>('code');
  const [copiedState, setCopiedState] = useState<string | null>(null);
  const { isDark } = useTheme();

  // Parse code execution data using GPT-5 helper
  const executionData = useMemo((): CodeExecutionData => {
    return gpt5Helper.parseCodeExecutionData(toolCall);
  }, [toolCall]);

  // Auto-expand on error or when there's output
  useEffect(() => {
    if (toolCall.status === 'error' || executionData.output || executionData.error) {
      setIsExpanded(true);
    }
    
    // Set initial tab based on content
    if (toolCall.status === 'error' && executionData.error) {
      setActiveTab('error');
    } else if (executionData.output) {
      setActiveTab('output');
    }
  }, [toolCall.status, executionData.output, executionData.error]);

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

  // Format execution time
  const formatExecutionTime = (time: number) => {
    if (time < 1000) return `${time}ms`;
    return `${(time / 1000).toFixed(2)}s`;
  };

  // Render code with syntax highlighting
  const renderCode = (code: string, language: string, type: string) => (
    <div className="relative">
      <button
        onClick={() => handleCopy(code, type)}
        className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
        style={{
          backgroundColor: 'var(--icui-bg-secondary)',
          borderColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-secondary)'
        }}
        title={copiedState === type ? 'Copied!' : 'Copy content'}
      >
        {copiedState === type ? (
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
      
      <SyntaxHighlighter
        language={language}
        style={isDark ? oneDark : oneLight}
        customStyle={{
          margin: 0,
          fontSize: '0.875rem',
          lineHeight: '1.5'
        }}
        showLineNumbers={true}
        wrapLines={true}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );

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
            <span className="text-lg">💻</span>
            <Terminal size={16} className="flex-shrink-0" />
            <div className="min-w-0">
              <div 
                className="font-medium text-sm"
                style={{ color: 'var(--icui-text-primary)' }}
              >
                Code Execution
              </div>
              <div 
                className="text-xs opacity-70"
                style={{ color: 'var(--icui-text-secondary)' }}
              >
                {executionData.environment} • {executionData.language}
                {executionData.executionTime && (
                  <span> • {formatExecutionTime(executionData.executionTime)}</span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {executionData.exitCode !== undefined && (
            <div 
              className="text-xs font-mono px-2 py-1 rounded"
              style={{
                backgroundColor: executionData.exitCode === 0 ? 'var(--icui-bg-success)' : 'var(--icui-bg-error)',
                color: executionData.exitCode === 0 ? 'var(--icui-text-success)' : 'var(--icui-text-error)'
              }}
            >
              Exit: {executionData.exitCode}
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
          {/* Progress Bar for Running Status */}
          {toolCall.status === 'running' && (
            <div className="p-3 border-b" style={{ borderColor: 'var(--icui-border-subtle)' }}>
              <div className="flex items-center gap-2">
                <Play size={16} className="text-blue-500 animate-pulse" />
                <span className="text-sm" style={{ color: 'var(--icui-text-primary)' }}>
                  Executing...
                </span>
              </div>
              <div className="mt-2 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 animate-pulse"
                  style={{ width: toolCall.progress ? `${toolCall.progress}%` : '30%' }}
                />
              </div>
            </div>
          )}

          {/* Content Tabs */}
          <div 
            className="flex border-b"
            style={{ borderColor: 'var(--icui-border-subtle)' }}
          >
            <button
              onClick={() => setActiveTab('code')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'code' 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent hover:border-gray-300'
              }`}
              style={{ color: activeTab === 'code' ? 'var(--icui-accent)' : 'var(--icui-text-secondary)' }}
            >
              Code
            </button>
            
            {executionData.output && (
              <button
                onClick={() => setActiveTab('output')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'output' 
                    ? 'border-blue-500 text-blue-600' 
                    : 'border-transparent hover:border-gray-300'
                }`}
                style={{ color: activeTab === 'output' ? 'var(--icui-accent)' : 'var(--icui-text-secondary)' }}
              >
                Output
              </button>
            )}
            
            {executionData.error && (
              <button
                onClick={() => setActiveTab('error')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'error' 
                    ? 'border-red-500 text-red-600' 
                    : 'border-transparent hover:border-gray-300'
                }`}
                style={{ color: activeTab === 'error' ? '#ef4444' : 'var(--icui-text-secondary)' }}
              >
                <div className="flex items-center gap-1">
                  <AlertTriangle size={14} />
                  <span>Error</span>
                </div>
              </button>
            )}
          </div>

          {/* Tab Content */}
          <div>
            {/* Code Tab */}
            {activeTab === 'code' && executionData.code && 
              renderCode(executionData.code, executionData.language, 'code')
            }

            {/* Output Tab */}
            {activeTab === 'output' && executionData.output && (
              <div className="relative">
                <button
                  onClick={() => handleCopy(executionData.output!, 'output')}
                  className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                  style={{
                    backgroundColor: 'var(--icui-bg-secondary)',
                    borderColor: 'var(--icui-border-subtle)',
                    color: 'var(--icui-text-secondary)'
                  }}
                  title={copiedState === 'output' ? 'Copied!' : 'Copy output'}
                >
                  {copiedState === 'output' ? (
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

                {executionData.outputFormat === 'json' ? (
                  <SyntaxHighlighter
                    language="json"
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {executionData.output}
                  </SyntaxHighlighter>
                ) : executionData.outputFormat === 'html' ? (
                  <SyntaxHighlighter
                    language="html"
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {executionData.output}
                  </SyntaxHighlighter>
                ) : executionData.outputFormat === 'markdown' ? (
                  <SyntaxHighlighter
                    language="markdown"
                    style={isDark ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      fontSize: '0.875rem',
                      lineHeight: '1.5'
                    }}
                    showLineNumbers={true}
                    wrapLines={true}
                  >
                    {executionData.output}
                  </SyntaxHighlighter>
                ) : (
                  <pre 
                    className="p-4 text-sm font-mono whitespace-pre-wrap overflow-x-auto"
                    style={{ 
                      backgroundColor: isDark ? '#1e1e1e' : '#f8f8f8',
                      color: 'var(--icui-text-primary)'
                    }}
                  >
                    {executionData.output}
                  </pre>
                )}
              </div>
            )}

            {/* Error Tab */}
            {activeTab === 'error' && executionData.error && (
              <div 
                className="p-4"
                style={{ backgroundColor: 'var(--icui-bg-error)' }}
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-red-600 mb-2">Execution Error</div>
                    <pre 
                      className="text-sm whitespace-pre-wrap font-mono"
                      style={{ color: 'var(--icui-text-primary)' }}
                    >
                      {executionData.error}
                    </pre>
                    
                    {executionData.stackTrace && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm font-medium text-red-600 hover:text-red-700">
                          Stack Trace
                        </summary>
                        <pre 
                          className="mt-2 text-xs whitespace-pre-wrap font-mono p-2 rounded"
                          style={{ 
                            backgroundColor: 'var(--icui-bg-secondary)',
                            color: 'var(--icui-text-secondary)'
                          }}
                        >
                          {executionData.stackTrace}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Execution Info */}
          <div 
            className="p-3 border-t text-xs"
            style={{ 
              backgroundColor: 'var(--icui-bg-tertiary)',
              borderColor: 'var(--icui-border-subtle)',
              color: 'var(--icui-text-secondary)'
            }}
          >
            <div className="flex items-center gap-4">
              <span>Environment: {executionData.environment}</span>
              {executionData.executionTime && (
                <span>Duration: {formatExecutionTime(executionData.executionTime)}</span>
              )}
              {executionData.exitCode !== undefined && (
                <span>Exit Code: {executionData.exitCode}</span>
              )}
              {toolCall.startTime && (
                <span>Started: {toolCall.startTime.toLocaleTimeString()}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GPT5CodeExecutionWidget; 