/**
 * ProgressWidget Component
 * 
 * Simple, clean progress indicator for tool execution
 */

import React, { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';

export interface ProgressWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

const ProgressWidget: React.FC<ProgressWidgetProps> = ({
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

  // Get status icon
  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'running':
        return <Loader2 size={16} className="animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'error':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <Loader2 size={16} className="animate-spin text-blue-500" />;
    }
  };

  return (
    <div 
      className={`border rounded-lg ${className}`}
      style={{
        backgroundColor: 'transparent',
        borderColor: '#d1d5db',
        color: 'var(--icui-text-primary)'
      }}
    >
      {/* Simple header */}
      <div 
        className={`flex items-center gap-3 px-3 py-2 border-b ${expandable ? 'cursor-pointer hover:bg-gray-50' : ''}`}
        style={{ borderBottomColor: '#e5e7eb' }}
        onClick={handleToggleExpansion}
      >
        {expandable && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-500" />
            ) : (
              <ChevronRight size={14} className="text-gray-500" />
            )}
          </div>
        )}

        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>

        <div className="flex-1 min-w-0">
          <span className="text-sm" style={{ color: 'var(--icui-text-primary)' }}>
            {toolCall.status === 'running' ? 'Executing tools...' : 'Tool execution complete'}
          </span>
        </div>
      </div>

      {/* Simple expanded content */}
      {isExpanded && (
        <div className="px-3 py-2">
          <div className="text-xs text-gray-600">
            Status: {toolCall.status}
            {toolCall.startTime && toolCall.endTime && (
              <span className="ml-3">
                Duration: {((toolCall.endTime.getTime() - toolCall.startTime.getTime()) / 1000).toFixed(2)}s
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgressWidget; 