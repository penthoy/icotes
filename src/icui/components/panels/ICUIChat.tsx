/**
 * ICUI Chat Component
 * 
 * AI-powered chat interface for the ICUI framework, following the established patterns
 * from ICUITerminal.tsx, ICUIExplorer.tsx, and ICUIEditor.tsx.
 * 
 * Features:
 * - Backend chat service integration via useChatMessages hook
 * - Real-time message streaming and WebSocket connection
 * - Theme-aware UI using ICUI CSS variables
 * - Connection status monitoring
 * - Message history and persistence
 * - Copy/paste functionality
 * - Auto-scroll behavior
 * - Agent configuration and management
 * - Keyboard shortcuts and accessibility
 * - Error handling and notifications
 */

import React, { useRef, useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { useMediaUpload } from '../../hooks/useMediaUpload';
import { Square, Send, Paperclip, Mic, Wand2, RefreshCw, Settings } from 'lucide-react';
import ChatDropZone from '../media/ChatDropZone';
import { 
  useChatMessages, 
  useTheme, 
  ChatMessage as ChatMessageType, 
  ConnectionStatus,
  MessageOptions,
  notificationService 
} from '../../index';
import { useConfiguredAgents } from '../../../hooks/useConfiguredAgents';
import { CustomAgentDropdown } from '../menus/CustomAgentDropdown';

import ChatMessage from '../chat/ChatMessage';
import { useChatSearch } from '../../hooks/useChatSearch';
import { useChatSessionSync } from '../../hooks/useChatSessionSync';
import { chatBackendClient } from '../../services/chat-backend-client-impl';
import { useChatHistory } from '../../hooks/useChatHistory';

interface ICUIChatProps {
  className?: string;
  chatId?: string;
  autoConnect?: boolean;
  maxMessages?: number;
  persistence?: boolean;
  autoScroll?: boolean;
  onMessageSent?: (message: ChatMessageType) => void;
  onMessageReceived?: (message: ChatMessageType) => void;
  onConnectionStatusChange?: (status: ConnectionStatus) => void;
}

export interface ICUIChatRef {
  sendMessage: (content: string, options?: MessageOptions) => Promise<void>;
  clearMessages: () => Promise<void>;
  connect: () => Promise<boolean>;
  disconnect: () => void;
  scrollToBottom: () => void;
  focus: () => void;
  isConnected: boolean;
}

const ICUIChat = forwardRef<ICUIChatRef, ICUIChatProps>(({
  className = '',
  chatId,
  autoConnect = true,
  maxMessages = 100,
  persistence = true,
  autoScroll = true,
  onMessageSent,
  onMessageReceived,
  onConnectionStatusChange
}, ref) => {
  // Debug logging for component lifecycle
  const componentId = useRef(`ICUIChat-${Date.now()}-${Math.random().toString(36).substring(2)}`);
  
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[${componentId.current}] Chat component mounted, autoConnect: ${autoConnect}`);
    }
    return () => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[${componentId.current}] Chat component unmounted`);
      }
    };
  }, [autoConnect]);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState('');
  const [selectedAgent, setSelectedAgent] = useState(''); // Default agent will be set by CustomAgentDropdown
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isComposing, setIsComposing] = useState(false);
  // NEW: smart auto-scroll state with user intent tracking
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const [hasNewMessages, setHasNewMessages] = useState(false);
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);
  const lastScrollTop = useRef(0);
  // Local staged attachments (minimal Phase 4.1 test implementation)
  const [staged, setStaged] = useState<{ id: string; file: File; preview: string }[]>([]);
  const uploadApi = useMediaUpload({ autoStart: true });

  // Watch upload queue for completed chat-context items and stage them (only new additions)
  useEffect(() => {
    uploadApi.uploads.forEach(u => {
      if (u.context === 'chat' && u.status === 'completed' && u.result && !staged.find(s => s.id === u.id)) {
        // Already have preview from creation; leave as-is
      }
    });
  }, [uploadApi.uploads, staged]);

  // Use the chat messages hook for backend integration
  const {
    messages,
    connectionStatus,
    isLoading,
    isTyping,
    sendMessage,
    sendCustomAgentMessage,
    stopStreaming,
    clearMessages,
    connect,
    disconnect,
    reloadMessages,
    isConnected,
    hasMessages,
    scrollToBottom
  } = useChatMessages({
    // Avoid auto-connecting before a session is known to prevent generating orphan sessions
    autoConnect: !!(typeof window !== 'undefined' && (localStorage.getItem('icui.chat.active_session') || chatBackendClient.currentSession)) && autoConnect,
    maxMessages,
    persistence,
    autoScroll
  });

  // Chat search hook (Ctrl+F)
  const search = useChatSearch(messages);

  // Session synchronization
  const { onSessionChange, emitSessionChange } = useChatSessionSync('ICUIChat');

  // Chat history management
  const { createSession, switchSession, sessions, activeSession, renameSession } = useChatHistory();

  // Track the globally-selected session (source: shared chat client + session sync)
  const [currentSessionId, setCurrentSessionId] = useState<string>(chatBackendClient.currentSession || '');
  const [currentSessionName, setCurrentSessionName] = useState<string | undefined>(undefined);
  const [isRenamingTitle, setIsRenamingTitle] = useState(false);
  const [tempTitle, setTempTitle] = useState('');

  // Compute title by preferring the most-recent event-provided name, then sessions list
  const sessionTitle = (() => {
    // Prefer event-provided name which updates immediately on rename
    if (currentSessionName && currentSessionName.trim().length > 0) return currentSessionName;
    const match = sessions.find(s => s.id === currentSessionId);
    return match?.name || 'Untitled Chat';
  })();

  // Start inline rename on header title
  const beginRenameTitle = useCallback(() => {
    if (!currentSessionId) return;
    setIsRenamingTitle(true);
    setTempTitle(sessionTitle);
  }, [currentSessionId, sessionTitle]);

  const cancelRenameTitle = useCallback(() => {
    setIsRenamingTitle(false);
    setTempTitle('');
  }, []);

  const saveRenameTitle = useCallback(async () => {
    const next = tempTitle.trim();
    setIsRenamingTitle(false);
    if (!currentSessionId) return;
    if (!next || next === sessionTitle) {
      setTempTitle('');
      return;
    }
    try {
      await renameSession(currentSessionId, next);
      // Update local title immediately; store event will also propagate
      setCurrentSessionName(next);
    } catch (e) {
      console.error('Failed to rename session from Chat header:', e);
    } finally {
      setTempTitle('');
    }
  }, [currentSessionId, tempTitle, renameSession, sessionTitle]);

  // Get available custom agents
  const { agents: configuredAgents, isLoading: agentsLoading, error: agentsError } = useConfiguredAgents();
  const customAgents = configuredAgents.map(agent => agent.name);

  // Use theme detection (following ICUITerminal pattern)
  const { isDark } = useTheme();

  // Theme detection effect (following ICUITerminal pattern with debouncing)
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const detectTheme = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const isDarkMode = document.documentElement.classList.contains('dark') ||
                          document.body.classList.contains('dark') ||
                          document.documentElement.classList.contains('icui-theme-github-dark') ||
                          document.documentElement.classList.contains('icui-theme-monokai') ||
                          document.documentElement.classList.contains('icui-theme-one-dark') ||
                          window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        setIsDarkTheme(isDarkMode);
      }, 100);
    };

    detectTheme();
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, []);

  // Auto-scroll when new messages arrive, but only if user hasn't intentionally scrolled up
  useEffect(() => {
    if (!messagesEndRef.current) return;
    if (!autoScroll) return;

    // Only auto-scroll if user is at bottom AND hasn't intentionally scrolled up
    if (isAutoScrollEnabled && !userHasScrolledUp) {
      // Use instant scroll to avoid jitter during streaming
      messagesEndRef.current.scrollIntoView({ behavior: 'auto' });
      setHasNewMessages(false);
    } else {
      // User is reading older messages or has scrolled up; show CTA
      setHasNewMessages(true);
    }
  }, [messages, autoScroll, isAutoScrollEnabled, userHasScrolledUp]);

  // Track user scroll position to enable/disable auto-scroll with intent detection
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    let ticking = false;
    const thresholdPx = 96; // within 96px of bottom is considered "at bottom"

    const handleScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const currentScrollTop = container.scrollTop;
        const distanceFromBottom = container.scrollHeight - (container.scrollTop + container.clientHeight);
        const nearBottom = distanceFromBottom <= thresholdPx;
        
        // Detect if user manually scrolled up (not caused by new content)
        const scrolledUp = currentScrollTop < lastScrollTop.current;
        
        // Update states based on user behavior
        setIsAutoScrollEnabled(nearBottom);
        
        if (scrolledUp && !nearBottom) {
          // User intentionally scrolled up away from bottom
          setUserHasScrolledUp(true);
        } else if (nearBottom) {
          // User is back at bottom, re-enable auto-scrolling
          setUserHasScrolledUp(false);
          setHasNewMessages(false);
        }
        
        lastScrollTop.current = currentScrollTop;
        ticking = false;
      });
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    // Initialize state based on current position
    handleScroll();
    return () => container.removeEventListener('scroll', handleScroll as any);
  }, []);

  // Jump to latest helper
  const jumpToLatest = useCallback(() => {
    setIsAutoScrollEnabled(true);
    setUserHasScrolledUp(false); // Reset user scroll intent
    setHasNewMessages(false);
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  // Notify parent of connection status changes
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[${componentId.current}] Connection status changed:`, connectionStatus);
    }
    onConnectionStatusChange?.(connectionStatus);
  }, [connectionStatus, onConnectionStatusChange]);

  // Listen for session changes from Chat History panel
  useEffect(() => {
    // Initialize from chat client once on mount
    if (chatBackendClient.currentSession) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[${componentId.current}] Initializing with existing session: ${chatBackendClient.currentSession}`);
      }
      setCurrentSessionId(chatBackendClient.currentSession);
      // Ensure connection if we suppressed autoConnect earlier
      if (!isConnected) {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[${componentId.current}] Attempting to connect for existing session`);
        }
        connect().catch((error) => {
          console.error(`[${componentId.current}] Failed to connect for existing session:`, error);
        });
      }
    }

    const cleanup = onSessionChange((sessionId, action, sessionName) => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[${componentId.current}] Session change event:`, { sessionId, action, sessionName });
      }
      if (action === 'switch' || action === 'create') {
        if (sessionId !== currentSessionId) {
          setCurrentSessionId(sessionId);
          if (sessionName !== undefined) setCurrentSessionName(sessionName);
          reloadMessages(sessionId);
          setIsAutoScrollEnabled(true);
          setHasNewMessages(true);
          jumpToLatest();
        }
        if (!isConnected) {
          if (process.env.NODE_ENV === 'development') {
            console.log(`[${componentId.current}] Attempting to connect for session change`);
          }
          connect().catch((error) => {
            console.error(`[${componentId.current}] Failed to connect for session change:`, error);
          });
        }
      }
    });

    return cleanup;
  }, [onSessionChange, reloadMessages, jumpToLatest, currentSessionId, isConnected, connect]);

  // Handle sending a message
  const handleSendMessage = useCallback(async (content?: string, options?: MessageOptions) => {
    const messageContent = content || inputValue.trim();
    if (!messageContent) {
      return;
    }

    try {
      // Auto-create session if none exists
      if (!currentSessionId && sessions.length === 0) {
        // Create session with explicit name, matching manual button behavior
        const newSessionId = await createSession('New Chat');
        // Set the name immediately - don't rely on async session state updates
        const createdName = 'New Chat';
        setCurrentSessionId(newSessionId);
        setCurrentSessionName(createdName);
      }

      // Check if selected agent is a custom agent (from custom_agent.py registry)
      // Dynamic check based on available custom agents from the API
      const isCustomAgent = customAgents.includes(selectedAgent);
      
      if (isCustomAgent) {
        // Use custom agent API
        await sendCustomAgentMessage(messageContent, selectedAgent);
      } else {
        // Use regular chat API with agent options
        const messageOptions: MessageOptions = {
          agentType: selectedAgent as any, // Cast to AgentType
          streaming: true,
          ...options // Merge with any provided options
        };
        
        await sendMessage(messageContent, messageOptions);
      }
      
      // Clear input only if using the input field
      if (!content) {
        setInputValue('');
      }
      
      // After sending, re-enable auto-scroll and jump smoothly once
      setIsAutoScrollEnabled(true);
      setHasNewMessages(false);
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }

      // Focus back to input
      if (inputRef.current) {
        inputRef.current.focus();
      }

      // Notify parent
      onMessageSent?.({
        id: `user_${Date.now()}_${Math.random().toString(36).substring(2)}`,
        content: messageContent,
        sender: 'user',
        timestamp: new Date()
      });
      
    } catch (error) {
      console.error('Failed to send message:', error);
      notificationService.error('Failed to send message');
    }
  }, [inputValue, selectedAgent, sendMessage, sendCustomAgentMessage, onMessageSent, customAgents]);

  // Handle stopping streaming
  const handleStopStreaming = useCallback(async () => {
    try {
      await stopStreaming();
    } catch (error) {
      console.error('Failed to stop streaming:', error);
      notificationService.error('Failed to stop streaming');
    }
  }, [stopStreaming]);

  // Handle clearing messages
  const handleClearMessages = useCallback(async () => {
    try {
      await clearMessages();
      notificationService.show('Chat cleared', 'info');
    } catch (error) {
      console.error('Failed to clear messages:', error);
      notificationService.error('Failed to clear messages');
    }
  }, [clearMessages]);

  // Handle Enter key press (following simplechat pattern)
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        return;
      } else {
        // Send message or stop streaming with Enter
        e.preventDefault();
        if (!isComposing) {
          if (isTyping) {
            handleStopStreaming();
          } else {
            handleSendMessage();
          }
        }
      }
    }
  }, [handleSendMessage, handleStopStreaming, isComposing, isTyping]);

  // Handle input composition (for IME support)
  const handleCompositionStart = useCallback(() => {
    setIsComposing(true);
  }, []);

  const handleCompositionEnd = useCallback(() => {
    setIsComposing(false);
  }, []);

  // Focus the input
  const handleFocus = useCallback(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);



  // Handle message reception notification
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.sender !== 'user') {
        onMessageReceived?.(lastMessage);
      }
    }
  }, [messages, onMessageReceived]);

  // Expose methods via ref (following ICUITerminal pattern)
  useImperativeHandle(ref, () => ({
    sendMessage: handleSendMessage,
    clearMessages: handleClearMessages,
    connect,
    disconnect,
    scrollToBottom,
    focus: handleFocus,
    isConnected
  }), [handleSendMessage, handleClearMessages, connect, disconnect, scrollToBottom, handleFocus, isConnected]);

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    
    // Auto-resize textarea
    const target = e.target;
    target.style.height = 'auto';
  target.style.height = `${Math.min(target.scrollHeight, 220)}px`;
  }, []);

  // Drag & Drop handled by ChatDropZone to avoid duplicate enqueues

  const removeStaged = (id: string) => 
    setStaged(prev => {
      const item = prev.find(s => s.id === id);
      if (item?.preview) URL.revokeObjectURL(item.preview);
      return prev.filter(s => s.id !== id);
    });

  // Cleanup URLs on unmount
  const stagedRef = useRef(staged);
  useEffect(() => { stagedRef.current = staged; }, [staged]);
  useEffect(() => () => {
    stagedRef.current.forEach(s => s.preview && URL.revokeObjectURL(s.preview));
  }, []);

  // Clipboard paste (images) -> stage only (upload handled globally to avoid duplicates)
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      if (!e.clipboardData) return;
      // If global handler already processed (sets a custom data flag), skip
      if ((e as any)._icuiGlobalPasteHandled) return;
      const items = Array.from(e.clipboardData.items);
      const fileItems = items.filter(it => it.kind === 'file');
      if (fileItems.length === 0) return;
      const files: File[] = [];
      fileItems.forEach(it => {
        const f = it.getAsFile();
        if (f) files.push(f);
      });
      if (files.length === 0) return;
      // Only handle if at least one image/* to avoid intercepting generic clipboard
      const imageFiles = files.filter(f => f.type.startsWith('image/'));
      if (imageFiles.length === 0) return;
      imageFiles.forEach(file => {
        const preview = URL.createObjectURL(file);
        const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        setStaged(prev => [...prev, { id: tempId, file, preview }]);
      });
      // Do not enqueue here to avoid duplicate; global manager handles upload.
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [uploadApi]);

  return (
    <div 
      className={`icui-chat h-full flex flex-col relative ${className}`} 
      style={{ 
        backgroundColor: 'var(--icui-bg-primary)', 
  color: 'var(--icui-text-primary)',
  overflowX: 'hidden'
      }}
    >
      {/* Drop zone overlay limited to scroll area + composer, not header */}
      <ChatDropZone
        selector=".icui-chat-drop-scope"
        uploadApi={uploadApi}
        onFilesStaged={(files) => {
          files.forEach(file => {
            const preview = file.type.startsWith('image/') ? URL.createObjectURL(file) : '';
            const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
            setStaged(prev => [...prev, { id: tempId, file, preview }]);
          });
        }}
      />
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 border-b" 
        style={{ 
          backgroundColor: 'var(--icui-bg-secondary)', 
          borderBottomColor: 'var(--icui-border-subtle)' 
        }}
      >
        <div
          className="flex items-center space-x-3 select-none"
          onDoubleClick={() => { if (currentSessionId) beginRenameTitle(); }}
          title={currentSessionId ? 'Double‑click to rename • Enter to save • Esc to cancel' : 'Create or select a chat to rename'}
        >
          {/* Connection Status Indicator */}
          <div className={`w-2 h-2 rounded-full transition-colors ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          
          {/* Current Session Name / Inline Rename */}
          {isConnected ? (
            isRenamingTitle ? (
              <input
                value={tempTitle}
                onChange={(e) => setTempTitle(e.target.value)}
                onBlur={saveRenameTitle}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') saveRenameTitle();
                  if (e.key === 'Escape') cancelRenameTitle();
                }}
                className="text-sm px-2 py-0.5 rounded border bg-transparent outline-none"
                style={{ 
                  color: 'var(--icui-text-primary)',
                  borderColor: 'var(--icui-border-subtle)'
                }}
                autoFocus
              />
            ) : (
              <span
                className="text-sm cursor-text"
                style={{ color: 'var(--icui-text-primary)' }}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'F2') beginRenameTitle();
                }}
              >
                {sessionTitle}
              </span>
            )
          ) : (
            <span className="text-sm" style={{ color: 'var(--icui-text-error)' }}>Disconnected</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2">
          {/* New Chat Button */}
          <button
      onClick={async () => {
              try {
        const newSessionId = await createSession();
        switchSession(newSessionId);
        // Try to find the created session's name; fall back to a sensible default
        const created = sessions.find(s => s.id === newSessionId);
        const createdName = created?.name || 'New Chat';
        emitSessionChange(newSessionId, 'create', createdName);
        setCurrentSessionId(newSessionId);
        setCurrentSessionName(createdName);
              } catch (error) {
                console.error('Failed to create new chat session:', error);
                notificationService.error('Failed to create new chat session');
              }
            }}
            className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
            style={{ 
              backgroundColor: 'var(--icui-bg-tertiary)', 
              color: 'var(--icui-text-primary)' 
            }}
            title="New chat"
          >
            + New
          </button>

          {/* Clear Button */}
          {hasMessages && (
            <button
              onClick={handleClearMessages}
              className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
              style={{ 
                backgroundColor: 'var(--icui-bg-tertiary)', 
                color: 'var(--icui-text-primary)' 
              }}
              title="Clear chat history"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="icui-chat-drop-scope flex-1 relative flex flex-col" style={{ minHeight:0 }}>
        {/* Messages Container */}
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto p-3 relative"
          style={{ backgroundColor: 'var(--icui-bg-primary)', overflowX: 'hidden' }}
        >
        {/* Search overlay moved below in toolbar */}
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center space-x-2" style={{ color: 'var(--icui-text-muted)' }}>
              <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
              <span className="text-sm">Loading...</span>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center" style={{ color: 'var(--icui-text-muted)' }}>
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-lg mb-2">No messages yet</p>
              <p className="text-sm">Start a conversation below</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id} data-message-id={message.id}>
                              <ChatMessage 
                  message={message}
                  className=""
                  highlightQuery={search.isOpen ? search.query : ''}
                />
              </div>
            ))}
            <div ref={messagesEndRef} data-icui-chat-end />
            {isConnected && isTyping && (
              <div className="flex items-center gap-2 text-xs opacity-70 mt-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <span>Assistant is working…</span>
              </div>
            )}
            {/* Sticky jump-to-latest when user scrolls up */}
            {!isAutoScrollEnabled && hasNewMessages && (
              <div className="sticky bottom-2 flex justify-center z-10">
                <button
                  onClick={jumpToLatest}
                  className="px-3 py-1.5 text-xs rounded-full shadow border"
                  style={{
                    backgroundColor: 'var(--icui-bg-secondary)',
                    color: 'var(--icui-text-primary)',
                    borderColor: 'var(--icui-border-subtle)'
                  }}
                >
                  Jump to latest
                </button>
              </div>
            )}
          </div>
        )}
        </div>

        {/* Bottom Toolbar: Search + Input */}
        <div 
          className="p-3 space-y-2" 
          style={{ 
            backgroundColor: 'var(--icui-bg-primary)', 
            borderTopColor: 'var(--icui-border-subtle)',
            overflowX: 'hidden'
          }}
        >
          {/* Search bar pinned above input */}
          {search.isOpen && (
            <div className="space-y-2 border rounded p-3" style={{ borderColor: 'var(--icui-border-subtle)', backgroundColor: 'var(--icui-bg-primary)' }}>
              {/* existing search UI ... */}
              {/** retained below unchanged */}
            </div>
          )}

          <div className="space-y-2">
            {/* Modern Composer - preserves previous layout (textarea on top, controls at bottom) */}
            <div className="icui-composer">
              {staged.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2" data-chat-attachments>
                  {staged.map(att => (
                    <div key={att.id} className="relative group border rounded p-0.5" style={{ borderColor: 'var(--icui-border-subtle)' }}>
                      {att.preview ? (
                        <img src={att.preview} alt={att.file.name} className="w-8 h-8 object-cover rounded" />
                      ) : (
                        <div className="w-8 h-8 flex items-center justify-center text-[10px]" style={{ background: 'var(--icui-bg-secondary)', color: 'var(--icui-text-secondary)' }}>{att.file.name.split('.').pop()?.toUpperCase()}</div>
                      )}
                      <button
                        onClick={() => removeStaged(att.id)}
                        className="absolute -top-2 -right-2 bg-red-600 text-white w-4 h-4 rounded-full text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                        title="Remove"
                      >×</button>
                    </div>
                  ))}
                </div>
              )}
              {/* Body: textarea */}
              <div className="icui-composer__body" data-chat-input>
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyPress}
                  onCompositionStart={handleCompositionStart}
                  onCompositionEnd={handleCompositionEnd}
                  placeholder="Type your message…"
                  className="icui-composer__textarea"
                  style={{ color: 'var(--icui-text-primary)' }}
                  rows={1}
                  disabled={!isConnected}
                />
              </div>

              {/* Bottom controls row - dropdown + refresh + settings + send */}
              <div className="icui-composer__controls">
                <div className="flex items-center gap-2 min-w-0">
                  <CustomAgentDropdown
                    selectedAgent={selectedAgent}
                    onAgentChange={setSelectedAgent}
                    disabled={false}
                    className="flex-shrink-0"
                    showCategories={true}
                    showDescriptions={true}
                  />
                </div>
                <div className="flex items-center gap-2">
                  {isTyping ? (
                    <button
                      className="icui-button icui--danger"
                      onClick={handleStopStreaming}
                      title="Stop generation"
                    >
                      <Square size={16} />
                    </button>
                  ) : (
                    <button
                      className="icui-button"
                      onClick={() => handleSendMessage()}
                      disabled={!inputValue.trim() || !isConnected || isLoading}
                      title="Send message (Enter)"
                    >
                      <Send size={16} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

// Set display name for debugging
ICUIChat.displayName = 'ICUIChat';

export default ICUIChat;
