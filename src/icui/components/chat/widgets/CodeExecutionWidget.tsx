/**
 * CodeExecutionWidget Component
 * 
 * Displays code execution results from tool calls with:
 * - Code input/output with syntax highlighting
 * - Execution status and timing information
 * - Support for multiple output formats (text, JSON, HTML, etc.)
 * - Error handling and stack traces
 * - Copy functionality for code and results
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { ChevronDown, ChevronRight, Play, Clock, Copy, Check, CheckCircle, AlertTriangle, Terminal } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../../hooks/useTheme';
import { ToolCallData } from '../ToolCallWidget';
import { getActiveModelHelper } from '../modelhelper';

export interface CodeExecutionWidgetProps {
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

const CodeExecutionWidget: React.FC<CodeExecutionWidgetProps> = ({
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

  // Parse code execution data using active model helper
  const executionData = useMemo((): CodeExecutionData => {
    const helper = getActiveModelHelper();
    return helper.parseCodeExecutionData(toolCall);
  }, [toolCall]);

  // Determine which tabs to show based on content
  const availableTabs = useMemo(() => {
    const tabs: Array<'code' | 'output' | 'error'> = ['code'];
    if (executionData.output) tabs.push('output');
    if (executionData.error || executionData.stackTrace) tabs.push('error');
    return tabs;
  }, [executionData.output, executionData.error, executionData.stackTrace]);

  // Ensure activeTab is valid
  useEffect(() => {
    if (!availableTabs.includes(activeTab)) {
      setActiveTab(availableTabs[0]);
    }
  }, [availableTabs, activeTab]);

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

  // Get status info
  const getStatusInfo = () => {
    if (toolCall.status === 'error' || (executionData.exitCode !== undefined && executionData.exitCode !== 0)) {
      return { color: 'text-red-500', icon: <AlertTriangle size={12} /> };
    }
    if (toolCall.status === 'success') {
      return { color: 'text-green-500', icon: <CheckCircle size={12} /> };
    }
    if (toolCall.status === 'running') {
      return { color: 'text-blue-500', icon: <Play size={12} className="animate-pulse" /> };
    }
    return { color: 'text-yellow-500', icon: <Terminal size={12} /> };
  };

  const statusInfo = getStatusInfo();

  // Render output based on format
  const renderOutput = useCallback((content: string, format: string) => {
    if (!content) return <div className="text-gray-500 italic">No output</div>;

    // Clean up content formatting
    let cleanContent = content
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .trim();

    // Simple text output without syntax highlighting
    return (
      <pre 
        className="whitespace-pre-wrap text-sm font-mono p-3 rounded overflow-x-auto"
        style={{ 
          backgroundColor: 'var(--icui-bg-tertiary)',
          color: 'var(--icui-text-primary)'
        }}
      >
        {cleanContent}
      </pre>
    );
  }, [isDark]);

  return (
    <div className={`icui-widget ${className}`}>
      {/* Header */}
      <div className={`icui-widget__header ${expandable ? 'icui--clickable' : ''}`} onClick={handleToggleExpansion}>
        {/* Expansion indicator */}
        {expandable && (
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

        {/* Execution info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="icui-widget__title">Code Execution</span>
            <span className={`text-xs px-2 py-0.5 rounded ${statusInfo.color}`}>
              {(executionData.language || 'text').toUpperCase()}
            </span>
            {executionData.exitCode !== undefined && (
              <span className={`text-xs px-2 py-0.5 rounded ${
                executionData.exitCode === 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                Exit {executionData.exitCode}
              </span>
            )}
          </div>
          {executionData.executionTime && (
            <div className="icui-widget__meta mt-1 flex items-center gap-1">
              <Clock size={12} />
              <span>{executionData.executionTime}ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div>
          {/* Tabs */}
          <div className="icui-widget__tabs">
            {availableTabs.map((tab) => {
              const isActive = activeTab === tab;
              
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`icui-widget__tab ${isActive ? 'icui--active' : ''}`}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === 'error' && (executionData.error || executionData.stackTrace) && (
                    <span className="ml-1 w-2 h-2 bg-red-500 rounded-full inline-block" />
                  )}
                </button>
              );
            })}

            <div className="flex-1" />

            {/* Copy button */}
            <button
              onClick={() => {
                let content = '';
                switch (activeTab) {
                  case 'code':
                    content = executionData.code;
                    break;
                  case 'output':
                    content = executionData.output || '';
                    break;
                  case 'error':
                    content = executionData.error || executionData.stackTrace || '';
                    break;
                }
                handleCopy(content, activeTab);
              }}
              className="flex items-center gap-1 px-3 py-2 text-xs rounded hover:bg-gray-200 text-gray-700 mr-3"
              title={`Copy ${activeTab}`}
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
          </div>

          {/* Content */}
          <div className="icui-widget__section">
            {activeTab === 'code' && (
              <SyntaxHighlighter
                language={executionData.language || 'text'}
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
                {executionData.code || 'No code available'}
              </SyntaxHighlighter>
            )}

            {activeTab === 'output' && (
              <div>
                {executionData.output ? (
                  renderOutput(executionData.output, executionData.outputFormat || 'text')
                ) : (
                  <div className="text-center py-8 text-gray-500 border border-dashed" style={{ borderColor: '#e5e7eb' }}>
                    No output produced
                  </div>
                )}
              </div>
            )}

            {activeTab === 'error' && (
              <div className="space-y-3">
                {executionData.error && (
                  <div>
                    <div className="text-sm font-medium text-red-600 mb-2">Error Message:</div>
                    <pre className="icui-widget__code text-red-700 border-red-200" style={{ backgroundColor: 'var(--icui-bg-error)' }}>{executionData.error}</pre>
                  </div>
                )}
                
                {executionData.stackTrace && (
                  <div>
                    <div className="text-sm font-medium text-red-600 mb-2">Stack Trace:</div>
                    <pre className="icui-widget__code text-xs text-red-700 border-red-200" style={{ backgroundColor: 'var(--icui-bg-error)' }}>{executionData.stackTrace}</pre>
                  </div>
                )}

                {!executionData.error && !executionData.stackTrace && (
                  <div className="text-center py-8 text-gray-500">
                    No errors
                  </div>
                )}
              </div>
            )}
          </div>

          {toolCall.status === 'running' && typeof toolCall.progress === 'number' && (
            <div className="px-3 pb-3">
              <div className="flex items-center gap-2 text-xs icui-widget__meta">
                <Play size={12} />
                <span>Executing code...</span>
                <span>{toolCall.progress}%</span>
              </div>
              <div className="icui-widget__progress mt-1">
                <div className="icui--bar" style={{ width: `${toolCall.progress}%` }} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CodeExecutionWidget;