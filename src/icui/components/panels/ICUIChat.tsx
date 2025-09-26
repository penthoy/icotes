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
import type { MediaAttachment as ChatMediaAttachment } from '../../types/chatTypes';
import { ICUI_FILE_LIST_MIME, isExplorerPayload } from '../../lib/dnd';
import { mediaService } from '../../services/mediaService';

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
  // Explorer referenced files (no upload – just path references)
  const [referenced, setReferenced] = useState<{ id: string; path: string; name: string; kind: 'file' }[]>([]);
  const composerRef = useRef<HTMLDivElement | null>(null);
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
    const messageContent = (content ?? inputValue).trim();
    // If there are pending uploads in chat context, start them
    const hasPending = uploadApi.uploads.some(u => u.context === 'chat' && u.status === 'pending');
    if (hasPending) {
      try { await uploadApi.uploadAll(); } catch { /* handled inside hook */ }
    }

    // Wait until all chat-context uploads are no longer pending/uploading (max ~15s)
    const waitForUploadsToSettle = async (timeoutMs = 15000) => {
      const start = Date.now();
      while (Date.now() - start < timeoutMs) {
        const busy = uploadApi.uploads.some(u => u.context === 'chat' && (u.status === 'pending' || u.status === 'uploading'));
        if (!busy) break;
        await new Promise(res => setTimeout(res, 150));
      }
    };
    await waitForUploadsToSettle();

    // Build attachments list from completed uploads in chat context (after settle)
    const completed = uploadApi.uploads.filter(u => u.context === 'chat' && u.status === 'completed' && u.result);
    const uploadAttachments: ChatMediaAttachment[] = completed.map(u => {
      const r: any = u.result!;
      const resKind = (r.kind || r.type || '').toString();
      const resMime = (r.mime_type || r.mime || '').toString();
      const resPath = (r.relative_path || r.rel_path || r.path || '').toString();
      const resSize = (typeof r.size_bytes === 'number' ? r.size_bytes : r.size) as number | undefined;
      const baseName = resPath ? resPath.split('/').pop() : (r.filename || undefined);
      const localKind: ChatMediaAttachment['kind'] = (
        resKind === 'images' || resKind === 'image' || (resMime && resMime.startsWith('image/'))
      ) ? 'image' : (
        resKind === 'audio' || (resMime && resMime.startsWith('audio/')) ? 'audio' : 'file'
      );
      return {
        id: r.id,
        kind: localKind,
        path: resPath,
        mime: resMime || 'application/octet-stream',
        size: typeof resSize === 'number' ? resSize : 0,
        meta: { source: 'upload', tempUploadId: u.id, filename: baseName }
      } as ChatMediaAttachment;
    });
    // Merge in referenced explorer files (kind = file)
    // Legacy: handle any remaining file references (should be rare now that explorer drops upload files)
    const referencedAttachments: ChatMediaAttachment[] = referenced.map(ref => {
      const mime = inferMimeFromName(ref.name);
      const isImage = mime.startsWith('image/');
      return {
        id: ref.id,
        kind: isImage ? 'image' : 'file',
        path: ref.path,
        mime,
        size: 0,
        meta: { source: 'explorer', filename: ref.name }
      } as ChatMediaAttachment;
    });
    const attachments = [...uploadAttachments, ...referencedAttachments];
    const hasText = messageContent.length > 0;
    const hasAttachments = attachments.length > 0;
    if (!hasText && !hasAttachments) {
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

  // Drag & Drop: handled globally via GlobalUploadManager and Explorer drop; Chat handles paste only

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
      // Enqueue uploads for chat context so they will be included on send
      uploadApi.addFiles(imageFiles, { context: 'chat' });
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [uploadApi]);

  // --- Explorer Drag & Drop (file references) ---
  // Infer basic mime type from filename (frontend only; backend may re-evaluate)
  const inferMimeFromName = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (!ext) return 'application/octet-stream';
    if (['png','jpg','jpeg','gif','webp','bmp','svg'].includes(ext)) return `image/${ext === 'jpg' ? 'jpeg' : ext}`;
    if (['mp3','wav','ogg','m4a','flac'].includes(ext)) return `audio/${ext}`;
    if (ext === 'json') return 'application/json';
    if (ext === 'md') return 'text/markdown';
    if (ext === 'txt' || ext === 'log') return 'text/plain';
    if (ext === 'html' || ext === 'htm') return 'text/html';
    if (ext === 'css') return 'text/css';
    if (ext === 'js' || ext === 'mjs' || ext === 'cjs' || ext === 'ts' || ext === 'tsx') return 'text/plain';
    if (ext === 'py') return 'text/x-python';
    return 'application/octet-stream';
  };

  useEffect(() => {
    const root = composerRef.current;
    if (!root) return;
    const handleDragOver = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      const types = Array.from(e.dataTransfer.types);
      const hasExplorerPayload = types.includes(ICUI_FILE_LIST_MIME);
      const hasFiles = types.includes('Files');
      if (!hasExplorerPayload && !hasFiles) return;
      e.preventDefault();
      setIsDragActive(true);
    };
    const handleDragLeave = (e: DragEvent) => {
      if (!(e.relatedTarget instanceof HTMLElement) || !root.contains(e.relatedTarget)) {
        setIsDragActive(false);
      }
    };
    const handleDrop = async (e: DragEvent) => {
      if (!e.dataTransfer) return;
      e.preventDefault();
      setIsDragActive(false);
      
      // Handle explorer internal drags (file references)
      const raw = e.dataTransfer.getData(ICUI_FILE_LIST_MIME);
      if (raw) {
        try {
          const payload = JSON.parse(raw);
          if (!isExplorerPayload(payload)) return;
          // Convert explorer file references to actual File objects and upload them
          // This makes explorer drops work identically to OS file drops
          const filePromises = payload.items
            .filter((item: any) => item.type === 'file')
            .map(async (item: any) => {
              try {
                const origin = window.location.origin.replace(/\/$/, '');
                const apiBase = origin.endsWith('/api') ? origin : `${origin}/api`;
                const rawUrl = `${apiBase}/files/raw?path=${encodeURIComponent(item.path)}`;
                
                const resp = await fetch(rawUrl);
                if (!resp.ok) return null;
                
                const blob = await resp.blob();
                return new File([blob], item.name, { type: blob.type });
              } catch (err) {
                console.warn('[ICUIChat] Failed to convert explorer item to File:', item.path, err);
                return null;
              }
            });
          
          // Wait for all file conversions and filter out nulls
          const files = (await Promise.all(filePromises)).filter(f => f !== null) as File[];
          
          if (files.length > 0) {
            // Upload to media and stage for chat (same as OS file drops)
            uploadApi.addFiles(files, { context: 'chat' });
            // Stage image previews immediately
            files.forEach(file => {
              if (file.type.startsWith('image/')) {
                const preview = URL.createObjectURL(file);
                const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
                setStaged(prev => [...prev, { id: tempId, file, preview }]);
              }
            });
          }
        } catch (err) {
          console.error('[ICUIChat] Failed to process explorer drag:', err);
        }
        return;
      }
      
      // Handle external OS file drops (actual uploads)
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        // Upload to media and stage for chat
        uploadApi.addFiles(files, { context: 'chat' });
        // Stage image previews immediately
        files.forEach(file => {
          if (file.type.startsWith('image/')) {
            const preview = URL.createObjectURL(file);
            const tempId = `staged-${Date.now()}-${Math.random().toString(36).slice(2)}`;
            setStaged(prev => [...prev, { id: tempId, file, preview }]);
          }
        });
      }
    };
    root.addEventListener('dragover', handleDragOver);
    root.addEventListener('dragleave', handleDragLeave);
    root.addEventListener('drop', handleDrop);
    return () => {
      root.removeEventListener('dragover', handleDragOver);
      root.removeEventListener('dragleave', handleDragLeave);
      root.removeEventListener('drop', handleDrop);
    };
  }, []);

  return (
    <div 
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
            <div ref={composerRef} className={`icui-composer ${isDragActive ? 'ring-2 ring-blue-400 rounded-md transition-colors' : ''}`} data-chat-composer>
              {(staged.length > 0 || referenced.length > 0) && (
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
                        console.warn('[ICUIChat] Failed to get base URL from mediaService, using window location:', error);
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
                      
                      console.log('[ICUIChat] Constructing image URL for Explorer reference:', {
                        path: ref.path,
                        encoded,
                        base: apiBase,
                        imageUrl,
                        name: ref.name
                      });
                      
                      return (
                        <div key={ref.id} className="relative group border rounded p-0.5" style={{ borderColor: 'var(--icui-border-subtle)' }} title={ref.path}>
                          <img 
                            src={imageUrl} 
                            alt={ref.name} 
                            className="w-8 h-8 object-cover rounded"
                            onError={async (e) => {
                              if (!e.currentTarget) return; // Safety guard for occasional nulls
                              console.warn('[ICUIChat] Direct raw file URL failed, attempting JSON content fallback', { directMediaUrl, fileContentUrl, path: ref.path });
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
                                    console.log('[ICUIChat] Fallback JSON->dataURL image applied');
                                    return;
                                  }
                                } else {
                                  console.warn('[ICUIChat] Fallback fetch failed status', resp.status);
                                }
                              } catch (err) {
                                console.error('[ICUIChat] Fallback fetch threw', err);
                              }
                              // Final placeholder if all else fails
                              e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIGZpbGw9IiMzZjQwNDYiIHJ4PSI0Ii8+PHBhdGggZD0iTTEwIDIwaDEyTTE2IDEyVjI0IiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBmaWxsPSJub25lIi8+PC9zdmc+';
                            }}
                            onLoad={() => {
                              console.log('[ICUIChat] Image preview loaded (explorer ref)', { url: imageUrl, path: ref.path });
                            }}
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
                      disabled={(!inputValue.trim() && !uploadApi.uploads.some(u => u.context === 'chat')) || !isConnected || isLoading}
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
