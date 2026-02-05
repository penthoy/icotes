/**
 * ProgressWidget Component
 * 
 * Simple, clean progress indicator for tool execution
 */

import React, { useState, useCallback, useEffect } from 'react';
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
  const [currentTime, setCurrentTime] = useState(Date.now());

  // Update current time every second when tool is running
  useEffect(() => {
    if (toolCall.status === 'running' && toolCall.startTime) {
      const interval = setInterval(() => {
        setCurrentTime(Date.now());
      }, 1000);
      return () => clearInterval(interval);
    } else if (toolCall.status !== 'running') {
      // Update one final time when tool finishes to capture the final duration
      setCurrentTime(Date.now());
    }
  }, [toolCall.status, toolCall.startTime]);

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  // Calculate execution time
  const getExecutionTime = () => {
    if (!toolCall.startTime) return null;
    
    const startTime = toolCall.startTime instanceof Date ? toolCall.startTime : new Date(toolCall.startTime);
    if (isNaN(startTime.getTime())) return null;
    
    // If tool has finished and endTime is set, use endTime
    if (toolCall.endTime && toolCall.status !== 'running') {
      const endTime = toolCall.endTime instanceof Date ? toolCall.endTime : new Date(toolCall.endTime);
      if (!isNaN(endTime.getTime())) {
        const seconds = ((endTime.getTime() - startTime.getTime()) / 1000).toFixed(2);
        return `${seconds}s`;
      }
    }
    
    // If tool is running, use currentTime for live updates
    // If tool is finished but endTime is invalid, use Date.now() (not stale currentTime)
    const timeToUse = toolCall.status === 'running' ? currentTime : Date.now();
    const seconds = ((timeToUse - startTime.getTime()) / 1000).toFixed(2);
    return `${seconds}s`;
  };

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
      </div>

      {/* Simple expanded content */}
      {isExpanded && (
        <div className="px-3 py-2">
          <div className="text-xs text-gray-600">
            Status: {toolCall.status}
            {getExecutionTime() && (
              <span className="ml-3">
                Duration: {getExecutionTime()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgressWidget; 