/**
 * WebSearchWidget Component
 *
 * Displays Tavily web_search inputs and outputs in a compact, readable way.
 */

import React, { useMemo, useState, useCallback } from 'react';
import { Globe, ChevronDown, ChevronRight, CheckCircle, XCircle, Clock } from 'lucide-react';
import { ToolCallData } from '../ToolCallWidget';

export interface WebSearchWidgetProps {
  toolCall: ToolCallData;
  className?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
}

const WebSearchWidget: React.FC<WebSearchWidgetProps> = ({
  toolCall,
  className = '',
  expandable = true,
  defaultExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getStatusInfo = () => {
    switch (toolCall.status) {
      case 'success':
        return { icon: <CheckCircle size={12} />, color: 'text-green-500' };
      case 'error':
        return { icon: <XCircle size={12} />, color: 'text-red-500' };
      case 'running':
        return { icon: <Clock size={12} />, color: 'text-blue-500' };
      default:
        return { icon: <Globe size={12} />, color: 'text-yellow-500' };
    }
  };

  const statusInfo = getStatusInfo();

  const handleToggleExpansion = useCallback(() => {
    if (expandable) setIsExpanded(prev => !prev);
  }, [expandable]);

  // Normalize input and output shapes for Tavily tool
  const { query, maxResults, searchDepth, includeAnswer } = useMemo(() => {
    const input = toolCall.input || {};
    let q: string | undefined = input.query || toolCall.metadata?.query;
    // Fallback: parse from raw args text recorded in metadata
    if (!q && toolCall.metadata?.argsText && typeof toolCall.metadata.argsText === 'string') {
      const m = toolCall.metadata.argsText.match(/['\"]query['\"]\s*:\s*['\"]([^'\"]+)['\"]/);
      if (m) q = m[1];
    }
    return {
      query: q || '(not provided)',
      maxResults: input.maxResults,
      searchDepth: input.searchDepth,
      includeAnswer: typeof input.includeAnswer === 'boolean' ? input.includeAnswer : undefined
    };
  }, [toolCall]);

  const normalized = useMemo(() => {
    const out = toolCall.output || {};
    // ToolResult(success=True, data={ answer, results: [...] }) could be passed directly as output or nested under .data
    const data = (out && out.data) ? out.data : out;
    const answer = data?.answer;
    const results = Array.isArray(data?.results) ? data.results : [];
    return { answer, results };
  }, [toolCall]);

  return (
    <div className={`icui-widget${className ? ` ${className}` : ''}`}>
      <button
        type="button"
        className={`icui-widget__header ${expandable ? 'icui--clickable' : ''}`}
        onClick={handleToggleExpansion}
        aria-expanded={isExpanded}
        aria-controls={`websearch-${toolCall.id}-panel`}
        disabled={!expandable}
      >
        <div className="flex-shrink-0">
          {expandable && (isExpanded ? (
            <ChevronDown size={14} className="text-gray-500" />
          ) : (
            <ChevronRight size={14} className="text-gray-500" />
          ))}
        </div>

        <span className="icui-chip">{toolCall.metadata?.originalToolName || toolCall.toolName}</span>
        {toolCall.status === 'running' && <span className="icui-spinner" aria-label="running" />}

        <div className={`flex-shrink-0 ${statusInfo.color}`}>{statusInfo.icon}</div>

        <span className="icui-widget__title">Web Search</span>
        <span className="icui-widget__meta truncate max-w-[40%]" title={query}>
          Query: <code>{query}</code>
        </span>
      </button>

      {isExpanded && (
        <div id={`websearch-${toolCall.id}-panel`} className="icui-widget__section space-y-3">
          {/* Parameters */}
          <div className="icui-widget__box p-2 text-xs space-y-1">
            <div>
              <strong>Query:</strong> <code>{query}</code>
            </div>
            {maxResults !== undefined && (
              <div>
                <strong>Max Results:</strong> <code>{String(maxResults)}</code>
              </div>
            )}
            {searchDepth && (
              <div>
                <strong>Depth:</strong> <code>{searchDepth}</code>
              </div>
            )}
            {includeAnswer !== undefined && (
              <div>
                <strong>Include Answer:</strong> <code>{String(includeAnswer)}</code>
              </div>
            )}
          </div>

          {/* Answer summary */}
          {normalized.answer && (
            <div className="icui-widget__box p-3 text-sm">
              <div className="font-semibold mb-1">Answer</div>
              <div className="whitespace-pre-wrap">{normalized.answer}</div>
            </div>
          )}

          {/* Results list */}
          <div className="space-y-2">
            {normalized.results && normalized.results.length > 0 ? (
              normalized.results.map((r: any, idx: number) => (
                <div key={idx} className="icui-widget__box p-2 text-sm">
                  <div className="font-medium truncate" title={r.title || r.url}>
                    {r.title || r.url || 'Untitled result'}
                  </div>
                  {r.url && (
                    <div className="text-xs icui-widget__meta truncate" title={r.url}>
                      {r.url}
                    </div>
                  )}
                  {r.content && (
                    <div className="text-xs mt-1 whitespace-pre-wrap opacity-80 line-clamp-6">
                      {r.content}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-xs icui-widget__meta">No results</div>
            )}
          </div>

          {/* Raw output for debugging */}
          {toolCall.output && (
            <details className="text-xs opacity-75">
              <summary className="cursor-pointer hover:opacity-100">Debug Info</summary>
              <div className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono whitespace-pre-wrap">
                {typeof toolCall.output === 'string' ? toolCall.output : JSON.stringify(toolCall.output, null, 2)}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default WebSearchWidget;
