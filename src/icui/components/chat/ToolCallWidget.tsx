/**
 * Base Tool Call Widget Component
 * 
 * Features:
 * - Progress indicators for tool execution
 * - Expandable tool call details
 * - Success/error states with visual feedback
 * - Different widget types based on tool category
 * - ICUI theme integration
 */

import React, { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, Wrench, Play } from 'lucide-react';

import { ToolCallStatus, ToolCallCategory } from '../../types/chatTypes';

export interface ToolCallData {
  id: string;
  toolName: string;
  category: ToolCallCategory;
  status: ToolCallStatus;
  progress?: number; // 0-100
  input?: any;
  output?: any;
  error?: string;
  startTime?: Date;
  endTime?: Date;
  metadata?: Record<string, any>;
}

export interface ToolCallWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

const ToolCallWidget: React.FC<ToolCallWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false,
  onRetry
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

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

  // Get status icon and color
  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'pending':
        return <Clock size={16} className="text-yellow-500" />;
      case 'running':
        return <Play size={16} className="text-blue-500 animate-pulse" />;
      case 'success':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'error':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <Wrench size={16} />;
    }
  };

  // Get category icon
  const getCategoryIcon = () => {
    switch (toolCall.category) {
      case 'file':
        return '📁';
      case 'code':
        return '💻';
      case 'network':
        return '🌐';
      case 'data':
        return '📊';
      case 'custom':
      default:
        return '🔧';
    }
  };

  // Calculate execution time
  const getExecutionTime = () => {
    if (toolCall.startTime && toolCall.endTime) {
      const startTime = toolCall.startTime instanceof Date ? toolCall.startTime : new Date(toolCall.startTime);
      const endTime = toolCall.endTime instanceof Date ? toolCall.endTime : new Date(toolCall.endTime);
      if (!isNaN(startTime.getTime()) && !isNaN(endTime.getTime())) {
        const seconds = ((endTime.getTime() - startTime.getTime()) / 1000).toFixed(2);
        return `Duration: ${seconds}s`;
      }
    } else if (toolCall.startTime) {
      const startTime = toolCall.startTime instanceof Date ? toolCall.startTime : new Date(toolCall.startTime);
      if (!isNaN(startTime.getTime())) {
        const seconds = ((Date.now() - startTime.getTime()) / 1000).toFixed(2);
        return `Duration: ${seconds}s`;
      }
    }
    return null;
  };

  return (
    <div 
      className={`tool-call-widget border rounded-lg p-3 my-2 transition-all ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)',
        color: 'var(--icui-text-primary)'
      }}
    >
      {/* Header */}
      <div 
        className={`flex items-center gap-3 ${expandable ? 'cursor-pointer' : ''}`}
        onClick={handleToggleExpansion}
      >
        {/* Expansion indicator */}
        {expandable && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown size={16} style={{ color: 'var(--icui-text-secondary)' }} />
            ) : (
              <ChevronRight size={16} style={{ color: 'var(--icui-text-secondary)' }} />
            )}
          </div>
        )}

        {/* Category icon */}
        <div className="flex-shrink-0 text-lg">
          {getCategoryIcon()}
        </div>

        {/* Tool name chip */}
        <span className="icui-chip">{toolCall.metadata?.originalToolName || toolCall.toolName}</span>

        {/* Tool name and status */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{toolCall.toolName}</span>
            {getStatusIcon()}
          </div>
          {/* Quick hint for web_search query when available */}
          {toolCall.toolName === 'web_search' && (
            <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--icui-text-secondary)' }}>
              {(() => {
                const input = toolCall.input || {};
                let q: string | undefined = input.query || toolCall.metadata?.query;
                if (!q && toolCall.metadata?.argsText && typeof toolCall.metadata.argsText === 'string') {
                  const m = toolCall.metadata.argsText.match(/['\"]query['\"]\s*:\s*['\"]([^'\"]+)['\"]/);
                  if (m) q = m[1];
                }
                return `Query: ${q || '(not provided)'}`;
              })()}
            </div>
          )}
          
          {/* Progress bar for running tools */}
          {toolCall.status === 'running' && typeof toolCall.progress === 'number' && (
            <div className="mt-1">
              <div 
                className="h-1 rounded-full overflow-hidden"
                style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}
              >
                <div 
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${toolCall.progress}%` }}
                />
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--icui-text-secondary)' }}>
                {toolCall.progress}% complete
              </div>
            </div>
          )}
        </div>

        {/* Execution time */}
        {getExecutionTime() && (
          <div className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
            {getExecutionTime()}
          </div>
        )}

        {/* Retry button for failed tools */}
        {toolCall.status === 'error' && onRetry && (
          <button
            onClick={handleRetry}
            className="px-2 py-1 text-xs rounded hover:opacity-80 transition-opacity"
            style={{
              backgroundColor: 'var(--icui-accent)',
              color: 'white'
            }}
          >
            Retry
          </button>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--icui-border-subtle)' }}>
          
          {/* Input section */}
          {toolCall.input && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold mb-1 uppercase tracking-wide" 
                  style={{ color: 'var(--icui-text-secondary)' }}>
                Input
              </h4>
              <div 
                className="p-2 rounded text-sm font-mono whitespace-pre-wrap break-all"
                style={{
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  color: 'var(--icui-text-primary)'
                }}
              >
                {typeof toolCall.input === 'string' 
                  ? toolCall.input 
                  : JSON.stringify(toolCall.input, null, 2)}
              </div>
            </div>
          )}

          {/* Output section */}
          {toolCall.output && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold mb-1 uppercase tracking-wide" 
                  style={{ color: 'var(--icui-text-secondary)' }}>
                Output
              </h4>
              <div 
                className="p-2 rounded text-sm font-mono whitespace-pre-wrap break-all"
                style={{
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  color: 'var(--icui-text-primary)'
                }}
              >
                {typeof toolCall.output === 'string' 
                  ? toolCall.output 
                  : JSON.stringify(toolCall.output, null, 2)}
              </div>
            </div>
          )}

          {/* Error section */}
          {toolCall.error && (
            <div className="mb-3">
              <h4 className="text-xs font-semibold mb-1 uppercase tracking-wide text-red-500">
                Error
              </h4>
              <div 
                className="p-2 rounded text-sm font-mono whitespace-pre-wrap break-all border border-red-300"
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  color: 'var(--icui-text-primary)'
                }}
              >
                {toolCall.error}
              </div>
            </div>
          )}

          {/* Metadata section */}
          {toolCall.metadata && Object.keys(toolCall.metadata).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold mb-1 uppercase tracking-wide" 
                  style={{ color: 'var(--icui-text-secondary)' }}>
                Metadata
              </h4>
              <div 
                className="p-2 rounded text-sm font-mono"
                style={{
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  color: 'var(--icui-text-primary)'
                }}
              >
                {Object.entries(toolCall.metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between items-start gap-2">
                    <span className="text-xs font-semibold" style={{ color: 'var(--icui-text-secondary)' }}>
                      {key}:
                    </span>
                    <span className="text-xs text-right">
                      {typeof value === 'string' ? value : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolCallWidget; 