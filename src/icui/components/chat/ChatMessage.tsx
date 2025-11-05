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
import { Copy, Check, Download, FileText, Play, Pause } from 'lucide-react';
import { ChatMessage as ChatMessageType, ToolCallMeta, MediaAttachment } from '../../types/chatTypes';
import { useTheme } from '../../hooks/useTheme';
import { ToolCallData } from './ToolCallWidget';
import { visit } from 'unist-util-visit';
import { getWidgetForTool } from '../../services/widgetRegistry';
import { getActiveModelHelper } from './modelhelper';
import { mediaService } from '../../services/mediaService';

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
  
  // Simple highlighter for plain text (user messages)
  const renderHighlightedPlainText = useCallback((text: string, query: string) => {
    if (!query || !text) return text;
    const q = query.toLowerCase();
    const parts: React.ReactNode[] = [];
    let i = 0;
    let start = 0;
    const lower = text.toLowerCase();
    while ((i = lower.indexOf(q, start)) !== -1) {
      if (i > start) {
        parts.push(text.slice(start, i));
      }
      const match = text.slice(i, i + q.length);
      parts.push(
        <mark key={`mark-${i}`} className="icui-mark">{match}</mark>
      );
      start = i + q.length;
    }
    if (start < text.length) parts.push(text.slice(start));
    return parts.length > 0 ? parts : text;
  }, []);
  
  // Attachment rendering helper
  const renderAttachment = useCallback((attachment: MediaAttachment, index: number) => {
    // Determine if this is an explorer reference (not an uploaded media asset)
    const isExplorerRef = Boolean(attachment.meta?.source === 'explorer' || String(attachment.id || '').startsWith('explorer-'));

    // Compute display filename
    const filename = (() => {
      // Prefer explicit filename from metadata (set during send)
      const explicit = attachment.meta?.filename;
      if (explicit && typeof explicit === 'string' && explicit.trim().length > 0) return explicit;
      const raw = (attachment.path ?? '').toString();
      const last = raw.split('/').pop();
      return last && last.length > 0 ? last : (attachment.kind === 'image' ? 'image' : attachment.kind === 'audio' ? 'audio' : 'file');
    })();

    // Build URL based on attachment source
    let url = '';
    if (isExplorerRef) {
      // For explorer references, use filesystem endpoints
      try {
        const base = (mediaService as any).apiUrl || mediaService["getFileUrl"]?.call(mediaService, 'files', '')?.replace(/\/media\/.*$/, '') || `${window.location.protocol}//${window.location.host}/api`;
        const encoded = encodeURIComponent(attachment.path);
        // For images/audio inline previews, prefer raw bytes; for downloads, use download endpoint
        if (attachment.kind === 'image' || attachment.kind === 'audio') {
          url = `${base.replace(/\/$/, '')}/files/raw?path=${encoded}`;
        } else {
          url = `${base.replace(/\/$/, '')}/files/download?path=${encoded}`;
        }
      } catch {
        // Fallback to raw endpoint path-only
        const encoded = encodeURIComponent(attachment.path);
        url = `/api/files/raw?path=${encoded}`;
      }
    } else {
      // For uploaded media, use media service endpoint
      url = mediaService.getAttachmentUrl(attachment as any);
    }
    const sizeKb = typeof attachment.size === 'number' ? (attachment.size / 1024) : undefined;
    
    switch (attachment.kind) {
      case 'image':
        return (
          <div key={attachment.id} className="relative group inline-block mr-1 mb-1">
            <img
              src={url}
              alt={`Attachment ${index + 1}`}
              className="rounded-md border shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              style={{
                border: '1px solid var(--icui-border-subtle)',
                backgroundColor: 'var(--icui-bg-secondary)',
                maxWidth: '120px',
                maxHeight: '120px',
                objectFit: 'cover'
              }}
              onClick={() => window.open(url, '_blank')}
            />
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  const link = document.createElement('a');
                  // For explorer refs, prefer download endpoint to force save
                  if (isExplorerRef) {
                    const encoded = encodeURIComponent(attachment.path);
                    const base = url.includes('/files/raw') ? url.replace(/\/files\/raw\?.*$/, '') : url.replace(/\/media\/file\/.*$/, '');
                    link.href = `${base}/files/download?path=${encoded}`;
                  } else {
                    link.href = url;
                  }
                  link.download = filename;
                  link.click();
                }}
                className="p-1 rounded bg-black bg-opacity-50 text-white hover:bg-opacity-70 transition-colors"
                title="Download image"
              >
                <Download size={14} />
              </button>
            </div>
          </div>
        );
      
      case 'audio':
        return (
          <div key={attachment.id} className="flex items-center gap-3 p-3 rounded-lg border mb-2 max-w-xs"
               style={{
                 border: '1px solid var(--icui-border-subtle)',
                 backgroundColor: 'var(--icui-bg-secondary)'
               }}>
            <audio controls className="flex-1 h-8">
              <source src={url} type={attachment.mime} />
              Your browser does not support audio playback.
            </audio>
            <button
              onClick={() => {
                const link = document.createElement('a');
                if (isExplorerRef) {
                  const encoded = encodeURIComponent(attachment.path);
                  const base = url.includes('/files/raw') ? url.replace(/\/files\/raw\?.*$/, '') : url.replace(/\/media\/file\/.*$/, '');
                  link.href = `${base}/files/download?path=${encoded}`;
                } else {
                  link.href = url;
                }
                link.download = filename;
                link.click();
              }}
              className="p-1 rounded hover:bg-opacity-10 hover:bg-current transition-colors"
              title="Download audio"
            >
              <Download size={16} />
            </button>
          </div>
        );
      
      case 'file':
      default:
        return (
          <div key={attachment.id} className="flex items-center gap-3 p-3 rounded-lg border mb-2 max-w-xs"
               style={{
                 border: '1px solid var(--icui-border-subtle)',
                 backgroundColor: 'var(--icui-bg-secondary)'
               }}>
            <FileText size={20} style={{ color: 'var(--icui-text-secondary)' }} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate" style={{ color: 'var(--icui-text-primary)' }}>
                {filename || 'Unknown file'}
              </div>
              <div className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
                {typeof sizeKb === 'number' ? `${sizeKb.toFixed(1)} KB` : ''}
              </div>
            </div>
            <button
              onClick={() => {
                const link = document.createElement('a');
                if (isExplorerRef) {
                  const encoded = encodeURIComponent(attachment.path);
                  // Use download endpoint for non-images
                  const base = url.includes('/files/') ? url.replace(/\/files\/.+$/, '') : (mediaService as any).apiUrl || '/api';
                  link.href = `${base.replace(/\/$/, '')}/files/download?path=${encoded}`;
                } else {
                  link.href = url;
                }
                link.download = filename || 'file';
                link.click();
              }}
              className="p-1 rounded hover:bg-opacity-10 hover:bg-current transition-colors"
              title="Download file"
            >
              <Download size={16} />
            </button>
          </div>
        );
    }
  }, []);
  
  // Simple remark plugin to wrap matches in <mark>
  const remarkHighlight = useMemo(() => {
    if (!highlightQuery) return undefined as any;
    const q = highlightQuery.toLowerCase();
    return () => (tree: any) => {
      visit(tree, 'text', (node: any, index: number, parent: any) => {
        const value: string = node.value;
        const lower = value.toLowerCase();
        if (!parent || typeof value !== 'string') return;
        let start = 0;
        let pos = lower.indexOf(q, start);
        if (pos === -1) return;
        const children: any[] = [];
        while (pos !== -1) {
          if (pos > start) {
            children.push({ type: 'text', value: value.slice(start, pos) });
          }
          const match = value.slice(pos, pos + q.length);
          children.push({ type: 'element', tagName: 'mark', properties: { className: ['icui-mark'] }, children: [{ type: 'text', value: match }] });
          start = pos + q.length;
          pos = lower.indexOf(q, start);
        }
        if (start < value.length) {
          children.push({ type: 'text', value: value.slice(start) });
        }
        parent.children.splice(index!, 1, ...children);
      });
    };
  }, [highlightQuery]);

  // Select active model helper
  const modelHelper = getActiveModelHelper();

  // Use model helper for text processing
  const stripAllToolText = modelHelper.stripAllToolText.bind(modelHelper);

  // Use model helper for parsing tool calls - memoized to prevent unnecessary re-parsing
  const parsedResult = useMemo((): { content: string; toolCalls: ToolCallData[] } => {
    const activeHelper = getActiveModelHelper();
    return activeHelper.parseToolCalls(message.content, message);
  }, [message.content, message.id, message.metadata?.streamComplete]);

  // Parse content sequentially to interleave remarks and tool calls robustly
  const sequentialBlocks = useMemo(() => {
    const blocks: Array<{ type: 'text' | 'toolCall'; content?: string; toolCall?: ToolCallData }> = [];
    const { content, toolCalls } = parsedResult;

    //

    // If no tool calls, just return cleaned content
    if (toolCalls.length === 0) {
      const clean = getActiveModelHelper().stripAllToolText(content || message.content || '');
      if (clean.trim()) blocks.push({ type: 'text', content: clean });
      return blocks;
    }

    // Build an index of tool calls grouped by execution block and ordered
    const grouped: Record<number, ToolCallData[]> = {};
    const ungrouped: ToolCallData[] = [];
    toolCalls.forEach(tc => {
      const b = Number.isInteger(tc.metadata?.blockIndex) ? (tc.metadata!.blockIndex as number) : undefined;
      if (b === undefined) {
        ungrouped.push(tc);
      } else {
        if (!grouped[b]) grouped[b] = [];
        grouped[b].push(tc);
      }
    });

    // Sort each group by indexInBlock or order for deterministic output
    Object.values(grouped).forEach(list => {
      list.sort((a, b) => {
        const ai = (a.metadata?.indexInBlock ?? a.metadata?.order ?? 0) as number;
        const bi = (b.metadata?.indexInBlock ?? b.metadata?.order ?? 0) as number;
        return ai - bi;
      });
    });

    // Split original content into alternating narration and execution blocks
    const original = message.content || '';
    const splitter = /(🔧\s*\*\*Executing tools\.\.\.\*\*[\s\S]*?)(?=🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*|$)/g;
    const segments: { kind: 'text' | 'exec'; value: string }[] = [];
    let lastIndex = 0;
    for (const m of original.matchAll(splitter)) {
      const idx = m.index ?? 0;
      if (idx > lastIndex) {
        segments.push({ kind: 'text', value: original.slice(lastIndex, idx) });
      }
      segments.push({ kind: 'exec', value: m[0] });
      lastIndex = idx + m[0].length;
    }
    if (lastIndex < original.length) {
      segments.push({ kind: 'text', value: original.slice(lastIndex) });
    }

    // Assemble blocks by iterating segments and injecting corresponding widgets
    let execBlockCursor = 0;
    segments.forEach(seg => {
      if (seg.kind === 'text') {
        const clean = getActiveModelHelper().stripAllToolText(seg.value);
        if (clean.trim()) blocks.push({ type: 'text', content: clean });
      } else {
        const tcs = grouped[execBlockCursor] || [];
        tcs.forEach(tc => blocks.push({ type: 'toolCall', toolCall: tc }));
        execBlockCursor++;
      }
    });

    // Append any ungrouped tool calls (e.g., emitted outside blocks) in their original order
    if (ungrouped.length > 0) {
      ungrouped
        .sort((a, b) => ((a.metadata?.order ?? 0) as number) - ((b.metadata?.order ?? 0) as number))
        .forEach(tc => blocks.push({ type: 'toolCall', toolCall: tc }));
    }

    //

    return blocks;
  }, [parsedResult, message.content]);

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
    const blockIdRef = React.useRef<string>(`${message.id}-${Math.random().toString(36).slice(2, 11)}`);
    const blockId = blockIdRef.current;
    const isCopied = copiedStates[blockId];

    //

    // Heuristic: Sometimes models emit fenced "```text\nword\n```" blocks for simple terms.
    // If it's a single short line with language empty/plain/text, render it as inline code instead
    // to avoid big block styling and the "text" label header.
    const raw = typeof children === 'string' ? children : String(children);
    const singleLine = !raw.includes('\n');
    const lang = (language || '').toLowerCase();
    const isPlainTextLang = !lang || lang === 'text' || lang === 'plaintext' || lang === 'plain';
    const looksInlineButBlock = !inline && singleLine && isPlainTextLang && raw.trim().length > 0 && raw.trim().length <= 48;

    if (looksInlineButBlock) {
      return (
        <code 
          className="px-1.5 py-0.5 rounded text-sm font-mono"
          style={{
            backgroundColor: 'var(--icui-bg-secondary)',
            color: 'var(--icui-text-primary)',
            border: '1px solid var(--icui-border-subtle)'
          }}
        >
          {raw}
        </code>
      );
    }

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
            onClick={() => handleCopy(typeof children === 'string' ? children : String(children), blockId)}
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
            {renderHighlightedPlainText(message.content, highlightQuery)}
          </div>
          
          {/* User Message Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-3">
              {message.attachments.map((attachment, index) => renderAttachment(attachment, index))}
            </div>
          )}
          
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
  const { content, toolCalls } = parsedResult;

  // Determine if any running tool widgets exist (used to suppress interim raw content)
  const hasRunningTools = toolCalls.some(tc => tc.status === 'running');
    
    // Check if this is a streaming message that contains tool execution text
    const isStreamingWithTools = message.metadata?.isStreaming && 
                                 message.content.includes('🔧 **Executing tools...**');
    
    // For streaming messages with tools, show content more permissively:
    // - Always show content if we have meaningful text after tool processing
    // - Only suppress if we're actively streaming tools AND have no parsed content
    const shouldShowContent = content &&
      // Don't suppress content just because we have running tools - let explanatory text show through
      !(isStreamingWithTools && !message.metadata?.streamComplete && toolCalls.length === 0 && !content.trim());
    
    // Show loading indicator only when we detect tool patterns but haven't parsed tools yet
    const shouldShowLoading = (isStreamingWithTools || hasRunningTools) &&
      !message.metadata?.streamComplete &&
      (toolCalls.length === 0 || hasRunningTools) &&
      !content.trim();
    
    return (
      <div className={`flex justify-start ${className}`}>
        <div className="w-full max-w-none">
          {/* Sequential Content - Interleaved text and tool calls */}
          {sequentialBlocks.map((block, index) => (
            <div key={`block-${index}`} className="mb-3">
              {block.type === 'text' ? (
                /* Text Block - Rendered as markdown */
                <div className="text-sm leading-relaxed prose prose-sm max-w-none" 
                     style={{ color: 'var(--icui-text-primary)' }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, ...(remarkHighlight ? [remarkHighlight] : [])]}
                    components={markdownComponents}
                  >
                    {block.content || ''}
                  </ReactMarkdown>
                </div>
              ) : (
                /* Tool Call Widget */
                (() => {
                  const Widget = getWidgetForTool(block.toolCall!.toolName);
                  return (
                    <Widget
                      toolCall={block.toolCall!}
                      expandable={true}
                      defaultExpanded={false}
                    />
                  );
                })()
              )}
            </div>
          ))}

          {/* Show loading indicator for streaming tool execution */}
          {shouldShowLoading && (
            <div className="flex items-center gap-2 text-sm py-2" style={{ color: 'var(--icui-text-secondary)' }}>
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              <span>Processing tools...</span>
            </div>
          )}

          {/* AI Message Attachments */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-3">
              {message.attachments.map((attachment, index) => renderAttachment(attachment, index))}
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

// Prevent re-render unless meaningful fields change
function areEqual(prev: ChatMessageProps, next: ChatMessageProps) {
  const a = prev.message; const b = next.message;
  if (a.id !== b.id) return false;
  if (a.content !== b.content) return false;
  // Streaming flags
  if (Boolean(a.metadata?.streamComplete) !== Boolean(b.metadata?.streamComplete)) return false;
  if (Boolean(a.metadata?.isStreaming) !== Boolean(b.metadata?.isStreaming)) return false;
  // Attachments fingerprint (ids/paths/sizes/mimes/kinds)
  const fp = (m?: ChatMessageType) =>
    (Array.isArray(m?.attachments) ? m!.attachments.map(att =>
      `${att.id ?? ''}|${att.path ?? ''}|${att.size ?? ''}|${(att as any).mime ?? ''}|${(att as any).kind ?? ''}`
    ).join(';') : '');
  if (fp(a) !== fp(b)) return false;
  // Highlight query affects rendering
  if (prev.highlightQuery !== next.highlightQuery) return false;
  return true;
}

export default React.memo(ChatMessage, areEqual); 