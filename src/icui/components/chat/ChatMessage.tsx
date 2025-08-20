/**
 * Enhanced Chat Message Component with Markdown Support
 * 
 * Features:
 * - Full markdown rendering with remark-gfm
 * - Syntax highlighting with Shiki (VS Code themes)
 * - Copy buttons for code blocks
 * - User message bubbles vs AI message clean layout
 * - ICUI theme integration
 * - Tool call widget support (future)
 */

import React, { useState, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { ChatMessage as ChatMessageType, ToolCallMeta } from '../../types/chatTypes';
import { useTheme } from '../../hooks/useTheme';
import { ToolCallData } from './ToolCallWidget';
import { visit } from 'unist-util-visit';
import { getWidgetForTool } from '../../services/widgetRegistry';

interface ChatMessageProps {
  message: ChatMessageType;
  className?: string;
  highlightQuery?: string;
}

interface CodeBlockProps {
  children: string;
  className?: string;
  inline?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, className = '', highlightQuery = '' }) => {
  const { isDark } = useTheme();
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  
  // Simple remark plugin to wrap matches in <mark>
  const remarkHighlight = useMemo(() => {
    if (!highlightQuery) return undefined as any;
    const q = highlightQuery.toLowerCase();
    return () => (tree: any) => {
      visit(tree, 'text', (node: any, index: number, parent: any) => {
        const value: string = node.value;
        const lower = value.toLowerCase();
        const idx = lower.indexOf(q);
        if (idx === -1 || !parent || typeof value !== 'string') return;
        const before = value.slice(0, idx);
        const match = value.slice(idx, idx + q.length);
        const after = value.slice(idx + q.length);
        const children: any[] = [];
        if (before) children.push({ type: 'text', value: before });
        children.push({ type: 'element', tagName: 'mark', properties: { className: ['icui-mark'] }, children: [{ type: 'text', value: match }] });
        if (after) children.push({ type: 'text', value: after });
        parent.children.splice(index!, 1, ...children);
      });
    };
  }, [highlightQuery]);

  // Parse tool calls from message content
  const parseToolCalls = useCallback((content: string): { content: string; toolCalls: ToolCallData[] } => {
    // Prefer toolCalls provided by backend in metadata
    const metaToolCalls: ToolCallMeta[] | undefined = message.metadata?.toolCalls;
    if (metaToolCalls && metaToolCalls.length > 0) {
      const toolCalls: ToolCallData[] = metaToolCalls.map(tc => ({
        id: tc.id,
        toolName: tc.toolName,
        category: (tc.category as any) || 'custom',
        status: (tc.status as any) || 'running',
        progress: typeof tc.progress === 'number' ? tc.progress : undefined,
        input: tc.input,
        output: tc.output,
        error: tc.error,
        startTime: tc.startedAt ? new Date(tc.startedAt) : undefined,
        endTime: tc.endedAt ? new Date(tc.endedAt) : undefined,
        metadata: tc.metadata
      }));
      return { content, toolCalls };
    }

    // Clean up content first to prevent flashing
    let cleanContent = content;

    // Remove escape sequences and clean up formatting
    cleanContent = cleanContent
      .replace(/\\n\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .replace(/logger\.(info|error|debug)\([^)]*\)/g, '')
      .trim();

    // Helper: try to parse python-like dicts to JSON
    const tryParseArgs = (text: string): any => {
      try {
        // Quick path: valid JSON
        return JSON.parse(text);
      } catch {}
      try {
        // Replace single quotes with double quotes and quote bare keys
        const quotedKeys = text
          .replace(/([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*):/g, '$1"$2"$3')
          .replace(/'/g, '"');
        return JSON.parse(quotedKeys);
      } catch {
        // Fallback: extract common fields from python-like dict string
        const fallback: any = { raw: text };
        const filePathMatch = text.match(/["']filePath["']\s*:\s*["']([^"']+)["']/);
        if (filePathMatch) fallback.filePath = filePathMatch[1];
        const startLineMatch = text.match(/["']startLine["']\s*:\s*(\d+)/);
        if (startLineMatch) fallback.startLine = parseInt(startLineMatch[1], 10);
        const endLineMatch = text.match(/["']endLine["']\s*:\s*(\d+)/);
        if (endLineMatch) fallback.endLine = parseInt(endLineMatch[1], 10);
        return fallback;
      }
    };

    // Enhanced pattern matching for tool execution blocks
    const toolExecutionPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n([\s\S]*?)🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*/g;
    const toolCalls: ToolCallData[] = [];
    let match;
    let toolCallIndex = 0;

    // First, check for standalone "🔧 **Executing tools...**" without completion
    const standaloneExecutingPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*(?!\s*\n[\s\S]*?🔧\s*\*\*Tool execution complete)/g;
    const standaloneMatches = Array.from(cleanContent.matchAll(standaloneExecutingPattern));

    // Only show progress widget for truly active executions (streaming messages)
    const isActiveStream = message.metadata?.isStreaming && !message.metadata?.streamComplete;

    if (standaloneMatches.length > 0 && isActiveStream) {
      // Create a progress widget for active tool execution
      const progressToolCall: ToolCallData = {
        id: `progress-${message.id}`,
        toolName: 'progress',
        category: 'custom',
        status: 'running',
        progress: undefined,
        input: { action: 'Executing tools...' },
        output: undefined,
        startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
        endTime: undefined,
        metadata: {
          isProgress: true,
          originalText: standaloneMatches[0][0]
        }
      };
      toolCalls.push(progressToolCall);
    }

    // Remove standalone executing indicators from content
    cleanContent = cleanContent.replace(standaloneExecutingPattern, '').trim();

    while ((match = toolExecutionPattern.exec(content)) !== null) {
      const toolBlock = match[1];
      const toolId = `tool-${message.id}-${toolCallIndex++}`;

      // Parse individual tool calls within the block - updated pattern for actual format
      const individualToolPattern = /📋\s*\*\*([^:]+)\*\*:\s*(\{[^}]*\}|\{[\s\S]*?\}|[^\n]*)\s*\n(✅\s*\*\*Success\*\*:\s*([\s\S]*?)(?=\n\n|📋|\n🔧|$)|❌\s*\*\*Error\*\*:\s*([\s\S]*?)(?=\n\n|📋|\n🔧|$))/g;

      let toolMatch;
      while ((toolMatch = individualToolPattern.exec(toolBlock)) !== null) {
        const toolName = toolMatch[1].trim();
        const inputText = toolMatch[2].trim();
        const isSuccess = toolMatch[0].includes('✅ **Success**');
        const resultText = isSuccess ? toolMatch[4] : toolMatch[5];

        // Parse input parameters (support both JSON and python-like dict)
        const input: any = inputText ? tryParseArgs(inputText) : {};

        // Parse the result/output for different tool types
        let parsedOutput: any = resultText?.trim();
        let parsedError: any = !isSuccess ? resultText?.trim() : undefined;

        if (isSuccess && parsedOutput) {
          try {
            // Try to parse as JSON first
            const jsonResult = JSON.parse(parsedOutput);
            parsedOutput = jsonResult;
          } catch {
            // For read_file, check if it's a structured response
            if (toolName.includes('read_file') && parsedOutput.includes('content')) {
              try {
                // Extract content from structured response
                const contentMatch = parsedOutput.match(/'content':\s*'([\s\S]*?)',\s*'filePath'/);
                if (contentMatch) {
                  parsedOutput = {
                    content: contentMatch[1].replace(/\\n/g, '\n').replace(/\\'/g, "'"),
                    filePath: input.filePath || 'unknown'
                  };
                }
              } catch {
                // Keep as string if parsing fails
              }
            } else if (toolName.includes('semantic_search') && parsedOutput.startsWith('[')) {
              try {
                // Parse array results
                parsedOutput = JSON.parse(parsedOutput.replace(/'/g, '"'));
              } catch {
                // Keep as string
              }
            }
          }
        }

        // Determine tool category and widget type
        let category: 'file' | 'code' | 'data' | 'network' | 'custom' = 'custom';
        let mappedToolName = toolName.toLowerCase().replace(/[^a-z0-9_]/g, '_');

        if (toolName.includes('read_file') || toolName.includes('create_file') || toolName.includes('replace_string')) {
          category = 'file';
          mappedToolName = 'file_edit';
        } else if (toolName.includes('run_in_terminal') || toolName.includes('execute') || toolName.includes('command')) {
          category = 'code';
          mappedToolName = 'code_execution';
        } else if (toolName.includes('semantic_search') || toolName.includes('search')) {
          category = 'data';
          mappedToolName = 'semantic_search';
        }

        const toolCall: ToolCallData = {
          id: `${toolId}-${toolName.replace(/[^a-zA-Z0-9]/g, '')}`,
          toolName: mappedToolName,
          category,
          status: isSuccess ? 'success' : 'error',
          progress: isSuccess ? 100 : 0,
          input,
          output: parsedOutput,
          error: parsedError,
          startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
          endTime: message.timestamp ? new Date(message.timestamp) : new Date(),
          metadata: {
            originalToolName: toolName,
            executionBlock: toolBlock.trim()
          }
        };

        toolCalls.push(toolCall);
      }
    }

    // Remove tool execution blocks from content but keep the rest
    cleanContent = content.replace(toolExecutionPattern, '').trim();

    // Also remove standalone "🔧 **Executing tools...**" indicators
    cleanContent = cleanContent.replace(/🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n?/g, '').trim();

    return {
      content: cleanContent,
      toolCalls
    };
  }, [message.id, message.metadata]);

  // Format timestamp helper
  const formatTimestamp = useCallback((timestamp: string | Date) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, []);

  // Handle code copy functionality
  const handleCopy = useCallback(async (code: string, blockId: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedStates(prev => ({ ...prev, [blockId]: true }));
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [blockId]: false }));
      }, 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  }, []);

  // Custom code block component with copy button
  const CodeBlock: React.FC<CodeBlockProps> = ({ children, className, inline }) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    const blockId = `${message.id}-${Math.random().toString(36).substr(2, 9)}`;
    const isCopied = copiedStates[blockId];

    if (inline) {
      return (
        <code 
          className="px-1.5 py-0.5 rounded text-sm font-mono"
          style={{
            backgroundColor: 'var(--icui-bg-secondary)',
            color: 'var(--icui-text-primary)',
            border: '1px solid var(--icui-border-subtle)'
          }}
        >
          {children}
        </code>
      );
    }

    return (
      <div className="relative group my-4">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 text-gray-200 text-sm rounded-t-lg">
          <span className="font-mono">{language || 'text'}</span>
          <button
            onClick={() => handleCopy(children, blockId)}
            className="flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
            title={isCopied ? 'Copied!' : 'Copy code'}
          >
            {isCopied ? (
              <>
                <Check size={14} />
                <span className="text-xs">Copied!</span>
              </>
            ) : (
              <>
                <Copy size={14} />
                <span className="text-xs">Copy</span>
              </>
            )}
          </button>
        </div>
        <SyntaxHighlighter
          language={language}
          style={isDark ? oneDark : oneLight}
          customStyle={{
            margin: 0,
            borderRadius: '0 0 0.5rem 0.5rem',
            fontSize: '0.875rem',
            lineHeight: '1.5'
          }}
          showLineNumbers={language !== ''}
          wrapLines={true}
        >
          {children}
        </SyntaxHighlighter>
      </div>
    );
  };

  // Markdown components configuration
  const markdownComponents = useMemo(() => ({
    code: CodeBlock,
    pre: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    
    // Style other markdown elements to match ICUI theme
    h1: ({ children }: { children: React.ReactNode }) => (
      <h1 className="text-2xl font-bold mb-4 pb-2 border-b" style={{ 
        color: 'var(--icui-text-primary)',
        borderColor: 'var(--icui-border-subtle)'
      }}>
        {children}
      </h1>
    ),
    h2: ({ children }: { children: React.ReactNode }) => (
      <h2 className="text-xl font-bold mb-3 mt-6" style={{ color: 'var(--icui-text-primary)' }}>
        {children}
      </h2>
    ),
    h3: ({ children }: { children: React.ReactNode }) => (
      <h3 className="text-lg font-semibold mb-2 mt-4" style={{ color: 'var(--icui-text-primary)' }}>
        {children}
      </h3>
    ),
    
    blockquote: ({ children }: { children: React.ReactNode }) => (
      <blockquote 
        className="border-l-4 pl-4 py-2 my-4 italic"
        style={{ 
          borderColor: 'var(--icui-accent)',
          backgroundColor: 'var(--icui-bg-secondary)',
          color: 'var(--icui-text-secondary)'
        }}
      >
        {children}
      </blockquote>
    ),
    
    table: ({ children }: { children: React.ReactNode }) => (
      <div className="overflow-x-auto my-4">
        <table 
          className="min-w-full border-collapse"
          style={{ borderColor: 'var(--icui-border-subtle)' }}
        >
          {children}
        </table>
      </div>
    ),
    
    th: ({ children }: { children: React.ReactNode }) => (
      <th 
        className="border px-4 py-2 text-left font-semibold"
        style={{ 
          borderColor: 'var(--icui-border-subtle)',
          backgroundColor: 'var(--icui-bg-secondary)',
          color: 'var(--icui-text-primary)'
        }}
      >
        {children}
      </th>
    ),
    
    td: ({ children }: { children: React.ReactNode }) => (
      <td 
        className="border px-4 py-2"
        style={{ 
          borderColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-primary)'
        }}
      >
        {children}
      </td>
    ),
    
    a: ({ href, children }: { href?: string; children: React.ReactNode }) => (
      <a 
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="underline hover:no-underline transition-all"
        style={{ color: 'var(--icui-accent)' }}
      >
        {children}
      </a>
    ),
    
    ul: ({ children }: { children: React.ReactNode }) => (
      <ul className="list-disc list-inside space-y-1 my-2 ml-4">
        {children}
      </ul>
    ),
    
    ol: ({ children }: { children: React.ReactNode }) => (
      <ol className="list-decimal list-inside space-y-1 my-2 ml-4">
        {children}
      </ol>
    ),
    
    li: ({ children }: { children: React.ReactNode }) => (
      <li style={{ color: 'var(--icui-text-primary)' }}>
        {children}
      </li>
    ),
    
    p: ({ children }: { children: React.ReactNode }) => (
      <p className="mb-3 leading-relaxed" style={{ color: 'var(--icui-text-primary)' }}>
        {children}
      </p>
    )
  }), [isDark, handleCopy, copiedStates, message.id]);

  if (message.sender === 'user') {
    // User messages: Keep chat bubble style (modern chat style)
    return (
      <div className={`flex justify-end ${className}`}>
        <div
          className="max-w-[85%] p-3 rounded-lg text-sm rounded-br-sm"
          style={{
            backgroundColor: 'var(--icui-bg-tertiary)',
            color: 'var(--icui-text-primary)',
            border: '1px solid var(--icui-border-subtle)'
          }}
        >
          {/* User Message Content - Simple text, no markdown */}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          
          {/* User Message Metadata */}
          <div className="flex items-center justify-end mt-2 text-xs" 
               style={{ color: 'var(--icui-text-secondary)' }}>
            <span>{formatTimestamp(message.timestamp)}</span>
          </div>
        </div>
      </div>
    );
    } else {
    // AI/Agent messages: Clean text layout with full markdown support
    const { content, toolCalls } = parseToolCalls(message.content);
    
    return (
      <div className={`flex justify-start ${className}`}>
        <div className="w-full max-w-none">
          {/* Tool Call Widgets */}
          {toolCalls.length > 0 && (
            <div className="mb-3">
              {toolCalls.map((toolCall) => {
                const Widget = getWidgetForTool(toolCall.toolName);
                return (
                  <Widget
                    key={toolCall.id}
                    toolCall={toolCall}
                    expandable={true}
                    defaultExpanded={false}
                  />
                );
              })}
            </div>
          )}

          {/* Agent Message Content - Full width with markdown rendering */}
          {content && (
            <div className="text-sm leading-relaxed prose prose-sm max-w-none" 
                 style={{ color: 'var(--icui-text-primary)' }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, ...(remarkHighlight ? [remarkHighlight] : [])]}
                components={markdownComponents}
              >
                {content}
              </ReactMarkdown>
            </div>
          )}
          
          {/* Agent Message Metadata */}
          {message.timestamp && (
            <div className="flex items-start justify-start mt-3 text-xs opacity-60" 
                 style={{ color: 'var(--icui-text-secondary)' }}>
              <span>{formatTimestamp(message.timestamp)}</span>
              {message.metadata?.agentId && (
                <>
                  <span className="mx-2">•</span>
                  <span>{message.metadata.agentId}</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }
};

export default ChatMessage; 