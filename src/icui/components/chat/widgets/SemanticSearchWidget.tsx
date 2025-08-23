/**
 * SemanticSearchWidget Component
 * 
 * Simple, clean display for semantic search results
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Search, ChevronDown, ChevronRight, CheckCircle, XCircle, Clock } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';
import { getActiveModelHelper } from '../modelhelper';
import { formatDisplayPath } from '../../../utils/pathUtils';

export interface SemanticSearchWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  onRetry?: (toolId: string) => void;
}

interface SearchResult {
  file: string;
  line?: number;
  snippet: string;
}

const SemanticSearchWidget: React.FC<SemanticSearchWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Parse search data using active model helper
  const searchData = useMemo(() => {
    const helper = getActiveModelHelper();
    return helper.parseSemanticSearchData(toolCall);
  }, [toolCall]);

  // Get status icon and color - unified with other widgets
  const getStatusInfo = () => {
    switch (toolCall.status) {
      case 'success':
        return { icon: <CheckCircle size={12} />, color: 'text-green-500' };
      case 'error':
        return { icon: <XCircle size={12} />, color: 'text-red-500' };
      case 'running':
        return { icon: <Clock size={12} />, color: 'text-blue-500' };
      default:
        return { icon: <Search size={12} />, color: 'text-yellow-500' };
    }
  };

  const statusInfo = getStatusInfo();

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  return (
    <div className={`icui-widget${className ? ` ${className}` : ''}`}>
      <div 
        className={`icui-widget__header ${isExpanded ? 'icui--clickable' : 'icui--clickable'}`}
        onClick={handleToggleExpansion}
      >
        {/* Expansion indicator */}
        <div className="flex-shrink-0">
          {isExpanded ? (
            <ChevronDown size={14} className="text-gray-500" />
          ) : (
            <ChevronRight size={14} className="text-gray-500" />
          )}
        </div>

        <span className="icui-chip">{toolCall.metadata?.originalToolName || toolCall.toolName}</span>
        {toolCall.status === 'running' && <span className="icui-spinner" aria-label="running" />}
        
        {/* Status icon */}
        <div className={`flex-shrink-0 ${statusInfo.color}`}>
          {statusInfo.icon}
        </div>

        <span className="icui-widget__title">Search Results</span>
        <span className="icui-widget__meta">
          {searchData.resultCount} result{searchData.resultCount !== 1 ? 's' : ''}
        </span>
        {!isExpanded && expandable && (
          <button 
            className="ml-auto text-xs px-2 py-1 text-gray-400 hover:text-gray-600"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(true);
            }}
          >
            Expand
          </button>
        )}
      </div>

      {/* Simple results */}
      {isExpanded && (
        <div className="icui-widget__section space-y-3">
          {/* Parameters */}
          <div className="icui-widget__box p-2 text-xs space-y-1">
            <div><strong>Query:</strong> <code>{searchData.query || '(not provided)'}</code></div>
            {searchData.scope && <div><strong>Scope:</strong> <code>{formatDisplayPath(searchData.scope)}</code></div>}
            {searchData.fileTypes && searchData.fileTypes.length > 0 && (
              <div><strong>Types:</strong> {searchData.fileTypes.join(', ')}</div>
            )}
          </div>

          {/* Results */}
          {searchData.resultCount > 0 ? (
            <div className="space-y-2">
              {searchData.results.map((result, index) => (
                <div key={index} className="text-sm">
                  <div className="font-mono text-xs icui-widget__meta">
                    {result.file}{result.line && `:${result.line}`}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs icui-widget__meta space-y-1">
              <div>No results found</div>
            </div>
          )}

          {/* Debug Info - always available for additional detail */}
          {toolCall.output && (
            <details className="text-xs opacity-75">
              <summary className="cursor-pointer hover:opacity-100">Debug Info</summary>
              <div className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">
                <div><strong>Raw Output:</strong></div>
                <div className="whitespace-pre-wrap">{JSON.stringify(toolCall.output, null, 2)}</div>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default SemanticSearchWidget; 