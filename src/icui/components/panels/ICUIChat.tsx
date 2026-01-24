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
import { 
  useChatMessages, 
  ChatMessage as ChatMessageType, 
  ConnectionStatus,
  MessageOptions,
  notificationService 
} from '../../index';
import { useConfiguredAgents } from '../../../hooks/useConfiguredAgents';
import { CustomAgentDropdown } from '../menus/CustomAgentDropdown';
import { resolveWorkspacePath } from '../../lib/workspaceUtils';

import ChatMessage from '../chat/ChatMessage';
import { useChatSearch } from '../../hooks/useChatSearch';
import { useChatSessionSync } from '../../hooks/useChatSessionSync';
import { chatBackendClient } from '../../services/chat-backend-client-impl';
import { useChatHistory } from '../../hooks/useChatHistory';
import type { MediaAttachment as ChatMediaAttachment } from '../../types/chatTypes';
import { mediaService } from '../../services/mediaService';
// Consolidated helpers to reduce file size and prevent regressions
import { inferMimeFromName } from '../chat/utils/mime';
import { waitForUploadsToSettle, buildAttachmentsFromUploads, buildReferencedAttachments } from '../chat/utils/sendPipeline';
import { useChatPaste } from '../chat/hooks/useChatPaste';
import { useComposerDnd } from '../chat/hooks/useComposerDnd';
import JumpToLatestButton from '../chat/widgets/JumpToLatestButton';

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
  const chatRootRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState('');
  const [selectedAgent, setSelectedAgent] = useState(''); // Default agent will be set by CustomAgentDropdown
  // Theme-dependent colors are provided via CSS variables; explicit theme state not required here
  const [isComposing, setIsComposing] = useState(false);
  // Local working state to show immediate feedback before streaming/typing events arrive
  const [isWorkingLocal, setIsWorkingLocal] = useState(false);
  // NEW: smart auto-scroll state with user intent tracking
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const [hasNewMessages, setHasNewMessages] = useState(false);
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);
  const lastScrollTop = useRef(0);
  // Local staged attachments (minimal Phase 4.1 test implementation)
  const [staged, setStaged] = useState<{ id: string; file: File; preview: string }[]>([]);
  // Explorer referenced files (no upload – just path references)
  const [referenced, setReferenced] = useState<{ id: string; path: string; name: string; kind: 'file' }[]>([]);
  // Composer element (callback ref) used for drag/drop binding
  const [composerEl, setComposerEl] = useState<HTMLDivElement | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
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
    // Disable hook-level auto-scroll when user has intentionally scrolled up
    autoScroll: autoScroll && !userHasScrolledUp
  });

  // Chat search hook (Ctrl+F) - context sensitive: only active when Chat has focus
  const search = useChatSearch(messages, {
    isActive: () => {
      try {
        const root = chatRootRef.current;
        const activeEl = typeof document !== 'undefined' ? document.activeElement : null;
        return !!(root && activeEl && root.contains(activeEl));
      } catch {
        return true; // fallback to previous behavior
      }
    }
  });

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
  // Note: We rely on CSS variables for theme; dynamic theme detection logic was removed as unused.

  // Auto-scroll when new messages arrive, but only if user hasn't intentionally scrolled up
  useEffect(() => {
    if (!messagesEndRef.current) return;
    if (!autoScroll) return;

    // Only auto-scroll if user was already at bottom and hasn't scrolled up
    // Use the state that's updated by the scroll handler, don't recalculate here
    if (isAutoScrollEnabled && !userHasScrolledUp) {
      // Small delay to ensure DOM has updated with new content
      requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
        }
      });
      setHasNewMessages(false);
    } else {
      // User is reading older messages; show "Jump to latest" button
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
        
        // Critical: Only update auto-scroll state based on MANUAL user scroll actions
        // Don't update if scroll was caused by auto-scroll itself
        if (scrolledUp && !nearBottom) {
          // User intentionally scrolled up away from bottom - LOCK auto-scroll OFF
          setUserHasScrolledUp(true);
          setIsAutoScrollEnabled(false);
        } else if (nearBottom && scrolledUp === false && currentScrollTop > lastScrollTop.current) {
          // User manually scrolled DOWN to bottom - re-enable auto-scrolling
          setUserHasScrolledUp(false);
          setIsAutoScrollEnabled(true);
          setHasNewMessages(false);
        }
        // Note: We don't update states if nearBottom becomes true due to new content arriving
        // This prevents the "pull back down" effect when user is reading older messages
        
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
    const messageContent = (content ?? inputValue).trim();
    // Determine early if we intend to send (text, referenced files, or any uploads in chat context)
    const intendsToSend =
      messageContent.length > 0 ||
      referenced.length > 0 ||
      uploadApi.uploads.some(u => u.context === 'chat');

    if (!intendsToSend) {
      return;
    }

    // Flip local working indicator immediately to avoid UX delay while uploads settle
    setIsWorkingLocal(true);
    // If there are pending uploads in chat context, start them
    const hasPending = uploadApi.uploads.some(u => u.context === 'chat' && u.status === 'pending');
    if (hasPending) {
      try { await uploadApi.uploadAll(); } catch { /* handled inside hook */ }
    }

    // Wait for uploads to settle using shared helper
    await waitForUploadsToSettle(() => uploadApi.uploads as any, 'chat', 15000, 150);

    // Build attachments list from completed uploads in chat context (after settle)
    const uploadAttachments: ChatMediaAttachment[] = buildAttachmentsFromUploads(uploadApi.uploads as any, 'chat');
    // Merge in referenced explorer files (kind = file)
    // Legacy: handle any remaining file references (should be rare now that explorer drops upload files)
    const referencedAttachments: ChatMediaAttachment[] = buildReferencedAttachments(referenced);
    const attachments = [...uploadAttachments, ...referencedAttachments];
    const hasText = messageContent.length > 0;
    const hasAttachments = attachments.length > 0;
    if (!hasText && !hasAttachments) {
      setIsWorkingLocal(false);
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
        await sendCustomAgentMessage(messageContent || '(attachment)', selectedAgent, { attachments });
      } else {
        // Use regular chat API with agent options
        const messageOptions: MessageOptions = {
          agentType: selectedAgent as any, // Cast to AgentType
          streaming: true,
          attachments,
          ...options // Merge with any provided options
        };
        
        await sendMessage(messageContent || '(attachment)', messageOptions);
      }

      // Hand off to hook-managed typing state; clear local indicator now that send started
      setIsWorkingLocal(false);
      
      // Clear input only if using the input field
      if (!content) {
        setInputValue('');
      }
      // Clear staged previews and completed uploads from queue after send
      setStaged(prev => {
        prev.forEach(s => s.preview && URL.revokeObjectURL(s.preview));
        return [];
      });
      uploadApi.clearCompleted();
      setReferenced([]);
      
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
      // Ensure local indicator is cleared on error
      setIsWorkingLocal(false);
    }
  }, [inputValue, selectedAgent, sendMessage, sendCustomAgentMessage, onMessageSent, customAgents, referenced.length, uploadApi.uploads]);

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

  // Drag & Drop: handled globally via GlobalUploadManager and Explorer drop; Chat handles paste only
  // Track uploads cancelled before they finish so we can delete them once they complete.
  const pendingCancelledUploadIds = useRef<Set<string>>(new Set());

  const removeStaged = (id: string) => 
    setStaged(prev => {
      const item = prev.find(s => s.id === id);
      if (item?.preview) URL.revokeObjectURL(item.preview);

      if (item?.file) {
        const matchingUpload = uploadApi.uploads.find(
          u => u.context === 'chat' && u.file === item.file
        );
        if (matchingUpload) {
          // Remove from queue (aborts if in-flight)
          uploadApi.removeFile(matchingUpload.id);
          if (matchingUpload.status === 'completed' && matchingUpload.result) {
            // Backend returns different key names than UploadResult interface; normalize here.
            const result: any = matchingUpload.result;
            const relPath: string | undefined = result.rel_path || result.relative_path;
            const kind: string = result.type || result.kind || 'files';
            const pathParts = relPath ? relPath.split('/') : [];
            const filename = pathParts[pathParts.length - 1];
            if (filename && kind) {
              if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
                console.debug('[Chat] Deleting cancelled completed upload', { id: matchingUpload.id, kind, filename, relPath });
              }
              mediaService.delete(kind, filename).catch(err => {
                console.warn('[Chat] Failed to delete cancelled upload from storage:', err);
              });
            } else {
              if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
                console.debug('[Chat] Skip deletion - missing filename/kind', { relPath, kind, result });
              }
            }
          } else {
            // Defer deletion until completion (small images may race with user clicking X)
            if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
              console.debug('[Chat] Deferring deletion until upload completes', { id: matchingUpload.id, status: matchingUpload.status });
            }
            pendingCancelledUploadIds.current.add(matchingUpload.id);
          }
        } else {
          if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
            console.debug('[Chat] removeStaged: no matching upload found for file');
          }
        }
      }
      return prev.filter(s => s.id !== id);
    });

  // Cleanup URLs on unmount
  const stagedRef = useRef(staged);
  useEffect(() => { stagedRef.current = staged; }, [staged]);
  useEffect(() => () => {
    stagedRef.current.forEach(s => s.preview && URL.revokeObjectURL(s.preview));
  }, []);

  // Deferred deletion watcher: when a previously cancelled upload finishes, delete its file.
  useEffect(() => {
    if (pendingCancelledUploadIds.current.size === 0) return;
    const finished: string[] = [];
    uploadApi.uploads.forEach(u => {
      if (pendingCancelledUploadIds.current.has(u.id) && u.status === 'completed' && u.result) {
        const result: any = u.result;
        const relPath: string | undefined = result.rel_path || result.relative_path;
        const kind: string = result.type || result.kind || 'files';
        const pathParts = relPath ? relPath.split('/') : [];
        const filename = pathParts[pathParts.length - 1];
        if (filename && kind) {
          if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
            console.debug('[Chat] Deferred deleting cancelled upload', { id: u.id, kind, filename, relPath });
          }
          mediaService.delete(kind, filename).catch(err => {
            console.warn('[Chat] Deferred delete failed for cancelled upload', u.id, err);
          });
        } else {
          if ((import.meta as any).env?.VITE_DEBUG_MEDIA === 'true') {
            console.debug('[Chat] Deferred deletion skipped - missing data', { id: u.id, relPath, kind });
          }
        }
        finished.push(u.id);
      }
    });
    if (finished.length) {
      finished.forEach(id => pendingCancelledUploadIds.current.delete(id));
    }
  }, [uploadApi.uploads]);

  // --- Explorer Drag & Drop (file references) ---
  // Moved mime inference to shared util to keep this file leaner

  // Replace inline DnD with hook to simplify component
  useComposerDnd(composerEl, {
    setActive: setIsDragActive,
    onRefs: (refs) => setReferenced(prev => [...prev, ...refs]),
    onFiles: (files) => {
      uploadApi.addFiles(files, { context: 'chat' });
      files.forEach(file => {
        const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        if (file.type.startsWith('image/')) {
          const preview = URL.createObjectURL(file);
          setStaged(prev => [...prev, { id: tempId, file, preview }]);
        } else {
          setStaged(prev => [...prev, { id: tempId, file, preview: '' }]);
        }
      });
    }
  });

  // Replace inline paste handler with hook
  useChatPaste(
    (file) => {
      const preview = URL.createObjectURL(file);
      const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      setStaged(prev => [...prev, { id: tempId, file, preview }]);
    },
    (files) => uploadApi.addFiles(files, { context: 'chat' })
  );

  return (
    <div 
      ref={chatRootRef}
      className={`icui-chat h-full flex flex-col relative ${className}`} 
      style={{ 
        backgroundColor: 'var(--icui-bg-primary)', 
  color: 'var(--icui-text-primary)',
  overflowX: 'hidden'
      }}
    >
      {/* No inline drop zone overlay; chat paste still supported */}
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
            {(() => {
              console.log('[STREAM-SURGICAL] ICUIChat rendering messages:', messages.length, 'items. IDs:', messages.map(m => m.id).join(', '));
              console.log('[STREAM-SURGICAL] Message contents:', messages.map(m => ({ id: m.id, sender: m.sender, content: m.content.substring(0, 50), isStreaming: m.metadata?.isStreaming })));
              return messages.map((message) => (
                <div key={message.id} data-message-id={message.id}>
                                <ChatMessage 
                    message={message}
                    className=""
                    highlightQuery={search.isOpen ? search.query : ''}
                  />
                </div>
              ));
            })()}
            <div ref={messagesEndRef} data-icui-chat-end />
            {isConnected && (isTyping || isWorkingLocal) && (
              <div className="flex items-center gap-2 text-xs opacity-70 mt-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <span>Assistant is working…</span>
              </div>
            )}
            {/* Sticky jump-to-latest when user scrolls up */}
            {!isAutoScrollEnabled && hasNewMessages && (
              <JumpToLatestButton onClick={jumpToLatest} />
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
            <div className="flex items-center gap-2 border rounded p-2" style={{ borderColor: 'var(--icui-border)', backgroundColor: 'var(--icui-bg-secondary)' }}>
              <input
                value={search.query}
                onChange={e => search.setQuery(e.target.value)}
                placeholder="Search..."
                className="text-sm px-2 py-1 rounded outline-none flex-1"
                style={{ 
                  color: 'var(--icui-text-primary)',
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  border: '1px solid var(--icui-border-subtle)'
                }}
                autoFocus
              />
              <span className="text-xs whitespace-nowrap" style={{ color: 'var(--icui-text-secondary)' }}>
                {search.results.length === 0 ? '0/0' : `${search.activeIdx + 1}/${search.results.length}`}
              </span>
              <button 
                className="text-xs px-2 py-1 rounded hover:opacity-80 whitespace-nowrap" 
                onClick={search.prev}
                style={{ 
                  color: 'var(--icui-text-primary)',
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  border: '1px solid var(--icui-border-subtle)'
                }}
              >
                Prev
              </button>
              <button 
                className="text-xs px-2 py-1 rounded hover:opacity-80 whitespace-nowrap" 
                onClick={search.next}
                style={{ 
                  color: 'var(--icui-text-primary)',
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  border: '1px solid var(--icui-border-subtle)'
                }}
              >
                Next
              </button>
              <button 
                className="text-xs px-2 py-1 rounded hover:opacity-80 whitespace-nowrap" 
                onClick={() => search.setIsOpen(false)}
                style={{ 
                  color: 'var(--icui-text-primary)',
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  border: '1px solid var(--icui-border-subtle)'
                }}
              >
                Close
              </button>
            </div>
          )}

          <div className="space-y-2">
            {/* Modern Composer - preserves previous layout (textarea on top, controls at bottom) */}
            <div ref={setComposerEl} className={`icui-composer ${isDragActive ? 'ring-2 ring-blue-400 rounded-md transition-colors' : ''}`} data-chat-composer>
              {(referenced.length > 0 || staged.length > 0) && (
                <div className="flex flex-wrap gap-2 mb-2 items-center" data-chat-attachments>
                  {referenced.map(ref => {
                    const mime = inferMimeFromName(ref.name);
                    const isImage = mime.startsWith('image/');
                    
                    if (isImage) {
                      // Render image preview for referenced files (Explorer drag)
                      // Use same URL construction pattern as ChatMessage component
                      const encoded = encodeURIComponent(ref.path);
                      
                      // Get base URL - try multiple methods for robustness
                      let base = '';
                      try {
                        base = (mediaService as any).apiUrl ||
                               mediaService.getAttachmentUrl({
                                 id: '',
                                 kind: 'image' as const,
                                 path: '',
                                 mime: 'image/png',
                                 size: 0,
                                 meta: {}
                               }).replace(/\/media\/file\/.*/, '') ||
                               `${window.location.protocol}//${window.location.host}`;
                      } catch (error) {
                        base = `${window.location.protocol}//${window.location.host}`;
                      }
                      // Normalize: remove trailing slash
                      base = base.replace(/\/$/, '');
                      // If base already ends with /api, do not add /api again
                      const hasApi = /\/api$/.test(base);
                      const apiBase = hasApi ? base : `${base}/api`;
                      // Prefer binary/media endpoint if available for direct image serving; fallback stays with JSON content endpoint transformed to data URL
                      const fileContentUrl = `${apiBase}/files/content?path=${encoded}`;
                      // Use new backend raw file endpoint for direct binary serving
                      const directMediaUrl = `${apiBase}/files/raw?path=${encoded}`;
                      // We'll optimistically try directMediaUrl; if it fails we'll fetch JSON and convert
                      const imageUrl = directMediaUrl;
                      
                      
                      
                      return (
                        <div key={ref.id} className="relative group border rounded p-0.5" style={{ borderColor: 'var(--icui-border-subtle)' }} title={ref.path}>
                          <img 
                            src={imageUrl} 
                            alt={ref.name} 
                            className="w-8 h-8 object-cover rounded"
                            onError={async (e) => {
                              if (!e.currentTarget) return; // Safety guard for occasional nulls
                              try {
                                const resp = await fetch(fileContentUrl);
                                if (resp.ok) {
                                  const json = await resp.json();
                                  const content = json?.data?.content;
                                  if (typeof content === 'string') {
                                    // Assume backend returned raw text; it might be binary base64 already or plain text.
                                    const looksBase64 = /^[A-Za-z0-9+/=\n\r]+$/.test(content) && content.length % 4 === 0;
                                    let dataUrl: string;
                                    if (looksBase64) {
                                      dataUrl = `data:${mime};base64,${content.replace(/\s+/g,'')}`;
                                    } else {
                                      const encodedTxt = encodeURIComponent(content);
                                      dataUrl = `data:${mime};charset=utf-8,${encodedTxt}`;
                                    }
                                    e.currentTarget.src = dataUrl;
                                    return;
                                  }
                                } else {
                                  // no-op; leave placeholder
                                }
                              } catch (err) {
                                // no-op; leave placeholder
                              }
                              // Final placeholder if all else fails
                              e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIGZpbGw9IiMzZjQwNDYiIHJ4PSI0Ii8+PHBhdGggZD0iTTEwIDIwaDEyTTE2IDEyVjI0IiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBmaWxsPSJub25lIi8+PC9zdmc+';
                            }}
                            onLoad={() => {/* no-op */}}
                          />
                          <button
                            onClick={() => setReferenced(prev => prev.filter(p => p.id !== ref.id))}
                            className="absolute -top-2 -right-2 bg-red-600 text-white w-4 h-4 rounded-full text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition"
                            title="Remove reference"
                          >×</button>
                        </div>
                      );
                    } else {
                      // Render non-image files as text labels
                      return (
                        <div key={ref.id} className="flex items-center gap-1 px-2 py-1 text-xs rounded border bg-opacity-40 group" style={{ borderColor: 'var(--icui-border-subtle)', background: 'var(--icui-bg-secondary)', color: 'var(--icui-text-primary)' }} title={ref.path}>
                          <span className="truncate max-w-[120px]">{ref.name}</span>
                          <button
                            onClick={() => setReferenced(prev => prev.filter(p => p.id !== ref.id))}
                            className="opacity-60 hover:opacity-100 transition-colors"
                            title="Remove reference"
                          >×</button>
                        </div>
                      );
                    }
                  })}
                  {staged.map(att => (
                    <div key={att.id} className="relative group border rounded p-1 flex items-center gap-2 max-w-[220px]" style={{ borderColor: 'var(--icui-border-subtle)', background: 'var(--icui-bg-secondary)' }} title={att.file.name}>
                      {att.preview ? (
                        <img 
                          src={att.preview} 
                          alt={att.file.name} 
                          className="w-8 h-8 object-cover rounded flex-shrink-0 cursor-pointer hover:ring-2 hover:ring-blue-400 transition" 
                          onClick={async () => {
                            // Open staged image in editor
                            try {
                              const matchingUpload = uploadApi.uploads.find(
                                u => u.context === 'chat' && u.file === att.file
                              );
                              
                              if (matchingUpload?.status === 'completed' && matchingUpload.result) {
                                const result: any = matchingUpload.result;
                                const relPath = result.rel_path || result.relative_path;
                                if (relPath) {
                                  // Construct absolute path using workspace root
                                  const fullPath = resolveWorkspacePath(`.icotes/media/${relPath}`);
                                  window.dispatchEvent(new CustomEvent('icui:openFile', {
                                    detail: { path: fullPath }
                                  }));
                                } else {
                                  notificationService.error('File path not available');
                                }
                              } else {
                                notificationService.info('File is still uploading, please wait...');
                              }
                            } catch (err) {
                              console.error('[Chat] Failed to open staged image:', err);
                              notificationService.error('Failed to open image preview');
                            }
                          }}
                          title="Click to preview in editor"
                        />
                      ) : (
                        <div className="w-8 h-8 flex items-center justify-center text-[10px] rounded flex-shrink-0" style={{ background: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-secondary)' }}>{att.file.name.split('.').pop()?.toUpperCase()}</div>
                      )}
                      <div className="min-w-0">
                        <div className="text-xs truncate" style={{ color: 'var(--icui-text-primary)' }}>{att.file.name}</div>
                      </div>
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
                      disabled={(!inputValue.trim() && !uploadApi.uploads.some(u => u.context === 'chat') && referenced.length === 0) || !isConnected || isLoading}
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
