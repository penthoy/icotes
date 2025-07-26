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
import { 
  useChatMessages, 
  useTheme, 
  ChatMessage, 
  ConnectionStatus,
  MessageOptions,
  notificationService 
} from '../index';

interface ICUIChatProps {
  className?: string;
  chatId?: string;
  autoConnect?: boolean;
  maxMessages?: number;
  persistence?: boolean;
  autoScroll?: boolean;
  onMessageSent?: (message: ChatMessage) => void;
  onMessageReceived?: (message: ChatMessage) => void;
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
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputValue, setInputValue] = useState('');
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isComposing, setIsComposing] = useState(false);

  // Use the chat messages hook for backend integration
  const {
    messages,
    connectionStatus,
    isLoading,
    sendMessage,
    clearMessages,
    connect,
    disconnect,
    isConnected,
    hasMessages,
    scrollToBottom
  } = useChatMessages({
    autoConnect,
    maxMessages,
    persistence,
    autoScroll
  });

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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  // Notify parent of connection status changes
  useEffect(() => {
    onConnectionStatusChange?.(connectionStatus);
  }, [connectionStatus, onConnectionStatusChange]);

  // Handle sending a message
  const handleSendMessage = useCallback(async (content?: string, options?: MessageOptions) => {
    const messageContent = content || inputValue.trim();
    if (!messageContent) return;

    try {
      await sendMessage(messageContent, options);
      
      // Clear input only if using the input field
      if (!content) {
        setInputValue('');
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
  }, [inputValue, sendMessage, onMessageSent]);

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
        // Send message with Enter
        e.preventDefault();
        if (!isComposing) {
          handleSendMessage();
        }
      }
    }
  }, [handleSendMessage, isComposing]);

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

  // Format timestamp (following simplechat pattern)
  const formatTimestamp = useCallback((date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
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
    target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
  }, []);

  return (
    <div 
      className={`icui-chat h-full flex flex-col ${className}`} 
      style={{ 
        backgroundColor: 'var(--icui-bg-primary)', 
        color: 'var(--icui-text-primary)' 
      }}
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 border-b" 
        style={{ 
          backgroundColor: 'var(--icui-bg-secondary)', 
          borderBottomColor: 'var(--icui-border-subtle)' 
        }}
      >
        <div className="flex items-center space-x-3">
          {/* Connection Status Indicator */}
          <div className={`w-2 h-2 rounded-full transition-colors ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`} />
          
          {/* Title and Agent Info */}
          <div className="flex flex-col">
            <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
              AI Assistant
            </span>
            {connectionStatus.agent && (
              <span className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                {connectionStatus.agent.name || connectionStatus.agent.type || 'Unknown'}
                {connectionStatus.agent.status && ` • ${connectionStatus.agent.status}`}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2">
          {/* Connection Status Text */}
          <span className="text-xs" style={{ 
            color: isConnected ? 'var(--icui-text-success)' : 'var(--icui-text-error)' 
          }}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          
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

      {/* Messages Container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-3"
        style={{ backgroundColor: 'var(--icui-bg-primary)' }}
      >
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
          <div className="space-y-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[95%] p-3 rounded-lg text-sm ${
                    message.sender === 'user' 
                      ? 'rounded-br-sm' 
                      : 'rounded-bl-sm'
                  }`}
                  style={{
                    backgroundColor: message.sender === 'user' 
                      ? 'var(--icui-bg-tertiary)' 
                      : 'var(--icui-bg-tertiary)',
                    color: 'var(--icui-text-primary)',
                    border: message.sender === 'user' 
                      ? '1px solid var(--icui-border-subtle)' 
                      : 'none'
                  }}
                >
                  {/* Message Content */}
                  <div className="whitespace-pre-wrap break-words">
                    {message.content}
                  </div>
                  
                  {/* Message Metadata */}
                  <div className="flex items-center justify-between mt-2 text-xs" 
                       style={{ color: 'var(--icui-text-muted)' }}>
                    <span>{formatTimestamp(message.timestamp)}</span>
                    {message.metadata?.agentType && (
                      <span className="ml-2">
                        {message.metadata.agentType}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div 
        className="p-3 border-t" 
        style={{ 
          backgroundColor: 'var(--icui-bg-secondary)', 
          borderTopColor: 'var(--icui-border-subtle)' 
        }}
      >
        <div className="flex space-x-3">
          {/* Message Input */}
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyPress}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder="Type your message..."
            className="flex-1 resize-none rounded-md border px-3 py-2 text-sm min-h-[38px] max-h-[120px] focus:outline-none transition-colors"
            style={{ 
              backgroundColor: 'var(--icui-bg-primary)', 
              color: 'var(--icui-text-primary)',
              borderColor: 'var(--icui-border-subtle)'
            }}
            rows={1}
            disabled={!isConnected}
          />
          
          {/* Send Button */}
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || !isConnected || isLoading}
            className="px-4 py-2 rounded-md text-sm font-medium hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2"
            style={{ 
              backgroundColor: 'var(--icui-accent)', 
              color: 'var(--icui-text-primary)'
            }}
            title="Send message (Enter)"
          >
            Send
          </button>
        </div>
        
        {/* Helper Text */}
        <div className="text-xs mt-2 flex items-center justify-between" 
             style={{ color: 'var(--icui-text-muted)' }}>
          <span>Press Enter to send • Shift+Enter for new line</span>
          {connectionStatus.agent?.capabilities && (
            <span>
              {connectionStatus.agent.capabilities.join(', ')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
});

// Set display name for debugging
ICUIChat.displayName = 'ICUIChat';

export default ICUIChat;
