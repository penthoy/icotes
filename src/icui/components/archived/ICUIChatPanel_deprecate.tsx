/**
 * ICUI Chat Panel - Reference Implementation
 * A minimal, working chat panel for AI/LLM/agent interface in the ICUI framework
 * Following the same pattern as ICUITerminalPanel
 */

import React, { useRef, useEffect, useState } from 'react';

interface ICUIChatPanelProps {
  className?: string;
}

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

const ICUIChatPanel: React.FC<ICUIChatPanelProps> = ({ className = '' }) => {
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      content: 'ICUIChatPanel initialized! How can I help you today?',
      sender: 'ai',
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(true); // Simulated connection state

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle sending a message
  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    // Simulate AI response after a short delay
    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `I received your message: "${inputValue}". This is a minimal chat implementation for testing purposes.`,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiResponse]);
    }, 1000);
  };

  // Handle Enter key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Clear chat messages
  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome',
        content: 'Chat cleared. How can I help you?',
        sender: 'ai',
        timestamp: new Date(),
      }
    ]);
  };

  return (
    <div className={`icui-chat-panel h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>AI Assistant</span>
        </div>
        <button
          onClick={handleClearChat}
          className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
          style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
        >
          Clear
        </button>
      </div>

      {/* Messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-2 space-y-3"
      >
        {messages.map((message) => (
          message.sender === 'user' ? (
            // User messages: Keep chat bubble style
            <div key={message.id} className="flex justify-end">
              <div
                className="max-w-[80%] p-2 rounded-lg text-sm"
                style={{
                  backgroundColor: 'var(--icui-bg-tertiary)',
                  color: 'var(--icui-text-primary)',
                  border: '1px solid var(--icui-border-subtle)'
                }}
              >
                <div>{message.content}</div>
                <div className="text-xs opacity-60 mt-1" style={{ color: 'var(--icui-text-secondary)' }}>
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ) : (
            // AI messages: Clean text layout, maximizing content area
            <div key={message.id} className="flex justify-start">
              <div className="w-full max-w-none">
                {/* Agent Message Content - Full width, no indentation */}
                <div className="text-sm" style={{ color: 'var(--icui-text-primary)' }}>
                  <div>{message.content}</div>
                </div>
              </div>
            </div>
          )
        ))}
      </div>

      {/* Input area */}
      <div className="p-2 border-t" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)' }}>
        <div className="flex space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 px-3 py-2 rounded-md border focus:outline-none text-sm"
            style={{ 
              backgroundColor: 'var(--icui-bg-primary)', 
              color: 'var(--icui-text-primary)',
              borderColor: 'var(--icui-border-subtle)'
            }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim()}
            className="px-4 py-2 rounded-md hover:opacity-80 disabled:opacity-50 disabled:cursor-not-allowed text-sm transition-opacity"
            style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default ICUIChatPanel;
