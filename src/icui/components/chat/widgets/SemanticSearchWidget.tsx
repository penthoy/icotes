/**
 * SemanticSearchWidget Component
 * 
 * Simple, clean display for semantic search results
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';

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

  // Parse search results
  const searchData = useMemo(() => {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    
    let results: SearchResult[] = [];
    let resultCount = 0;
    
    // Handle different output formats
    if (Array.isArray(output)) {
      // Direct array
      results = output.map((item: any) => ({
        file: item.file || 'Unknown file',
        line: item.line,
        snippet: item.snippet || ''
      }));
    } else if (output.result) {
      try {
        const parsed = JSON.parse(output.result);
        if (Array.isArray(parsed)) {
          results = parsed.map((item: any) => ({
            file: item.file || 'Unknown file',
            line: item.line,
            snippet: item.snippet || ''
          }));
        }
      } catch {
        // If parsing fails, show simple text
      }
    } else if (typeof output === 'string' && output.startsWith('[')) {
      try {
        const parsed = JSON.parse(output.replace(/'/g, '"'));
        if (Array.isArray(parsed)) {
          results = parsed.map((item: any) => ({
            file: item.file || 'Unknown file',
            line: item.line,
            snippet: item.snippet || ''
          }));
        }
      } catch {
        // Keep as empty if parsing fails
      }
    }
    
    resultCount = results.length;
    
    return {
      query: input.query || '',
      scope: input.scope || '',
      fileTypes: input.fileTypes || [],
      results,
      resultCount
    };
  }, [toolCall]);

  // Toggle expansion
  const handleToggleExpansion = useCallback(() => {
    if (expandable) {
      setIsExpanded(prev => !prev);
    }
  }, [expandable]);

  const formatFilePath = (path: string) => {
    if (path.startsWith('/home/penthoy/icotes/workspace/')) {
      return path.replace('/home/penthoy/icotes/workspace/', '');
    }
    return path;
  };

  return (
    <div className="icui-widget">
      <div 
        className={`icui-widget__header ${isExpanded ? 'icui--clickable' : 'icui--clickable'}`}
        onClick={() => setIsExpanded(!isExpanded)}
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
        <span className="icui-widget__title">Search Results</span>
        <span className="icui-widget__meta">
          {searchData.resultCount} result{searchData.resultCount !== 1 ? 's' : ''}
        </span>
        {!isExpanded && (
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
            {searchData.scope && <div><strong>Scope:</strong> <code>{formatFilePath(searchData.scope)}</code></div>}
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
                    {formatFilePath(result.file)}{result.line && `:${result.line}`}
                  </div>
                  <div className="mt-1 pl-2 border-l-2 border-gray-300 icui-widget__code text-xs">
                    {result.snippet}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs icui-widget__meta">No results found</div>
          )}
        </div>
      )}
    </div>
  );
};

export default SemanticSearchWidget; 