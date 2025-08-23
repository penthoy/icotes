import React, { useEffect, useRef } from 'react';
import { 
  useChatMessages, 
  useTheme, 
  ChatMessage, 
  notificationService 
} from '../../src/icui';
import { CustomAgentDropdown } from '../../src/icui/components/menus/CustomAgentDropdown';

interface SimpleChatProps {
  className?: string;
}

const SimpleChat: React.FC<SimpleChatProps> = ({ className = '' }) => {
  const { isDark } = useTheme();
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
    autoConnect: true,
    maxMessages: 100,
    autoScroll: true
  });

  const [inputValue, setInputValue] = React.useState('');
  const [selectedAgent, setSelectedAgent] = React.useState(''); // Default will be set by component from configuration
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    
    try {
      // Include the selected agent in the message options
      await sendMessage(inputValue, {
        agentType: selectedAgent as any, // Cast to AgentType
        streaming: true,
        context: {
          timestamp: new Date().toISOString()
        }
      });
      setInputValue('');
    } catch (error) {
      notificationService.error('Failed to send message');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className={`flex flex-col h-screen bg-white dark:bg-gray-900 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Simple Chat
          </h1>
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              <span className="text-sm font-medium">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {hasMessages && (
              <button
                onClick={clearMessages}
                className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
              >
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-500 dark:text-gray-400">Loading...</div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <p className="text-lg mb-2">No messages yet</p>
              <p className="text-sm">Start a conversation below</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            message.sender === 'user' ? (
              // User messages: Keep chat bubble style
              <div key={message.id} className="flex justify-end">
                <div className="max-w-xs lg:max-w-md px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-600">
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className="text-xs mt-1 text-gray-500 dark:text-gray-400">
                    {formatTimestamp(message.timestamp)}
                  </div>
                </div>
              </div>
            ) : (
              // AI messages: Clean text layout, maximizing content area
              <div key={message.id} className="flex justify-start">
                <div className="w-full max-w-none">
                  {/* Agent Message Content - Full width, no indentation */}
                  <div className="text-sm leading-relaxed text-gray-900 dark:text-white">
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  </div>
                </div>
              </div>
            )
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex space-x-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-blue-500 focus:outline-none"
            rows={1}
            disabled={!isConnected}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !isConnected}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Send
          </button>
        </div>
        
        {/* Agent Selection - Below Input */}
        <div className="mt-3">
          <CustomAgentDropdown
            selectedAgent={selectedAgent}
            onAgentChange={setSelectedAgent}
            disabled={!isConnected}
            className="w-full"
          />
        </div>
      </div>
    </div>
  );
};

export default SimpleChat;
