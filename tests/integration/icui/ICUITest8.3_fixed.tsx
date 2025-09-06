/**
 * ICUI Test 8.3 - Chat History Item Actions
 * 
 * Tests Step 8.3: Chat context menus with message-specific actions,
 * session management, and extensibility.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { 
  createChatContextMenu, 
  handleChatContextMenuClick, 
  ChatMenuContext,
  ChatMenuExtensions,
  registerChatCommand,
  createCustomChatMenuGroup
} from '../../../src/icui/components/menus/ChatContextMenu';
import { chatOperations } from '../../../src/icui/components/chat/ChatOperations';
import { ContextMenu } from '../../../src/icui/components/ui/ContextMenu';
import { MenuSchema, MenuContext, MenuItem } from '../../../src/icui/lib/menuSchemas';
import { globalCommandRegistry } from '../../../src/icui/lib/commandRegistry';
import { ChatMessage, MessageSender } from '../../../src/icui/types/chatTypes';
import { log } from '../../../src/services/frontend-logger';

/**
 * Mock chat data for testing
 */
const mockChatMessages: ChatMessage[] = [
  {
    id: '1',
    content: 'Hello! Can you help me with React components?',
    sender: 'user' as MessageSender,
    timestamp: new Date('2024-01-01T10:00:00Z'),
    metadata: {}
  },
  {
    id: '2',
    content: 'Of course! I\'d be happy to help you with React components. What specific aspect would you like to learn about?',
    sender: 'ai' as MessageSender,
    timestamp: new Date('2024-01-01T10:00:30Z'),
    metadata: {
      agentId: 'assistant-1',
      agentName: 'Code Assistant',
      agentType: 'openai'
    }
  },
  {
    id: '3',
    content: 'I\'m trying to understand how to use useEffect with dependencies.',
    sender: 'user' as MessageSender,
    timestamp: new Date('2024-01-01T10:01:00Z'),
    metadata: {}
  },
  {
    id: '4',
    content: 'Great question! The useEffect hook with dependencies is fundamental to React. Here\'s how it works:\n\n```javascript\nuseEffect(() => {\n  // Effect code here\n}, [dependency1, dependency2]);\n```\n\nThe dependency array controls when the effect runs.',
    sender: 'ai' as MessageSender,
    timestamp: new Date('2024-01-01T10:01:30Z'),
    metadata: {
      agentId: 'assistant-1',
      agentName: 'Code Assistant',
      agentType: 'openai'
    }
  }
];

/**
 * Register custom chat commands for testing
 */
const registerCustomChatCommands = () => {
  // Custom command: Analyze message sentiment
  registerChatCommand(
    'chat.analyzeSentiment',
    'Analyze Sentiment',
    async (context: ChatMenuContext) => {
      if (!context.selectedMessage) return;
      
      const message = context.selectedMessage;
      const sentiments = ['positive', 'neutral', 'negative'];
      const randomSentiment = sentiments[Math.floor(Math.random() * sentiments.length)];
      
      alert(`Message Sentiment Analysis:\n\nMessage: "${message.content.substring(0, 50)}..."\nSentiment: ${randomSentiment}\nConfidence: ${(Math.random() * 100).toFixed(1)}%`);
      log.info('CustomChatCommand', 'Analyzed sentiment', { messageId: message.id, sentiment: randomSentiment });
    },
    {
      icon: '🧠',
      description: 'Analyze the sentiment of the selected message',
    }
  );

  // Custom command: Translate message
  registerChatCommand(
    'chat.translateMessage',
    'Translate Message',
    async (context: ChatMenuContext) => {
      if (!context.selectedMessage) return;
      
      const languages = ['Spanish', 'French', 'German', 'Japanese', 'Chinese'];
      const randomLanguage = languages[Math.floor(Math.random() * languages.length)];
      
      alert(`Translation to ${randomLanguage}:\n\nOriginal: "${context.selectedMessage.content.substring(0, 50)}..."\nTranslated: "[Mock translation in ${randomLanguage}]"`);
      log.info('CustomChatCommand', 'Translated message', { 
        messageId: context.selectedMessage.id, 
        targetLanguage: randomLanguage 
      });
    },
    {
      icon: '🌐',
      description: 'Translate the selected message to another language',
    }
  );

  // Custom command: Save as note
  registerChatCommand(
    'chat.saveAsNote',
    'Save as Note',
    async (context: ChatMenuContext) => {
      if (!context.selectedMessage) return;
      
      const message = context.selectedMessage;
      const note = {
        id: Date.now().toString(),
        content: message.content,
        timestamp: new Date(),
        source: 'chat',
        messageId: message.id
      };
      
      // Mock save to notes system
      alert(`Note Saved!\n\nContent: "${message.content.substring(0, 100)}..."\nNote ID: ${note.id}`);
      log.info('CustomChatCommand', 'Saved message as note', { messageId: message.id, noteId: note.id });
    },
    {
      icon: '📝',
      description: 'Save the selected message as a note',
    }
  );
};

interface ContextMenuState {
  schema: MenuSchema;
  context: MenuContext;
  position: { x: number; y: number };
}

const ICUITest83: React.FC = () => {
  const [messages, setMessages] = useState<string[]>([]);
  const [selectedMessage, setSelectedMessage] = useState<ChatMessage | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(mockChatMessages);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  const addMessage = (message: string) => {
    setMessages(prev => [...prev.slice(-10), `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const showContextMenu = useCallback((event: React.MouseEvent, schema: MenuSchema, context: MenuContext) => {
    event.preventDefault();
    event.stopPropagation();
    
    setContextMenu({
      schema,
      context,
      position: { x: event.clientX, y: event.clientY }
    });
  }, []);

  const hideContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleMenuItemClick = useCallback((item: MenuItem) => {
    if (!contextMenu) return;
    
    // Execute the command via the global command registry
    globalCommandRegistry.execute(item.id, contextMenu.context)
      .then(() => {
        addMessage(`Context menu action: ${item.label} executed`);
      })
      .catch((error) => {
        log.warn('ICUITest8.3', 'Command execution failed', { commandId: item.id, error });
        addMessage(`Error: Command ${item.id} failed - ${error.message}`);
      });
    
    hideContextMenu();
  }, [contextMenu, hideContextMenu]);

  useEffect(() => {
    // Register custom commands when component mounts
    registerCustomChatCommands();
    log.info('ICUITest8.3', 'Registered custom Chat commands');
    
    return () => {
      // Cleanup: Unregister custom commands when component unmounts
      ['chat.analyzeSentiment', 'chat.translateMessage', 'chat.saveAsNote'].forEach(commandId => {
        globalCommandRegistry.unregister(commandId);
      });
      log.info('ICUITest8.3', 'Unregistered custom Chat commands');
    };
  }, []);

  const handleContextMenu = useCallback((event: React.MouseEvent, message?: ChatMessage) => {
    event.preventDefault();
    event.stopPropagation();

    // Create menu context with required properties
    const menuContext: ChatMenuContext = {
      panelType: 'chat',
      selectedMessage: message,
      chatMessages,
      canRename: true,
      canDelete: true,
      canExport: true,
      sessionId: 'test-session-123',
      messageCount: chatMessages.length
    };

    // Create menu extensions for testing
    const extensions: ChatMenuExtensions = {
      customCommands: [
        'chat.analyzeSentiment',
        'chat.translateMessage',
        'chat.saveAsNote'
      ],
      customGroups: [
        createCustomChatMenuGroup('analysis', [
          { id: 'chat.analyzeSentiment', label: 'Analyze Sentiment', icon: '🧠' }
        ], { 
          label: 'Analysis Tools',
          separator: true
        }),
        createCustomChatMenuGroup('translation', [
          { id: 'chat.translateMessage', label: 'Translate Message', icon: '🌐' }
        ], { 
          label: 'Translation',
          separator: true
        })
      ],
      hiddenItems: ['chat.markAsRead'] // Hide this default action for testing
    };

    const schema = createChatContextMenu(menuContext, extensions);
    
    showContextMenu(event, schema, menuContext);
  }, [chatMessages, showContextMenu]);

  const clearChat = () => {
    setChatMessages([]);
    setSelectedMessage(null);
    addMessage('Chat cleared');
  };

  const resetChat = () => {
    setChatMessages(mockChatMessages);
    setSelectedMessage(null);
    addMessage('Chat reset to mock data');
  };

  const addTestMessage = () => {
    const newMessage: ChatMessage = {
      id: `test-${Date.now()}`,
      content: `This is a test message added at ${new Date().toLocaleTimeString()}`,
      sender: 'user' as MessageSender,
      timestamp: new Date(),
      metadata: {}
    };
    setChatMessages(prev => [...prev, newMessage]);
    addMessage('Test message added');
  };

  return (
    <div style={{ 
      height: '100vh', 
      backgroundColor: '#1e1e1e', 
      color: '#ffffff', 
      fontFamily: 'monospace',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{ 
        padding: '20px', 
        borderBottom: '1px solid #444',
        backgroundColor: '#2d2d30'
      }}>
        <h2 style={{ margin: '0 0 10px 0', color: '#4FC3F7' }}>
          ICUI Test 8.3 - Chat History Item Actions
        </h2>
        <p style={{ margin: '0', color: '#ccc', fontSize: '14px' }}>
          Testing extensible context menus for chat history items with custom commands, 
          message-specific actions, and session management.
        </p>
      </div>

      {/* Controls */}
      <div style={{ 
        padding: '15px 20px', 
        backgroundColor: '#252526',
        borderBottom: '1px solid #444',
        display: 'flex',
        gap: '10px',
        flexWrap: 'wrap'
      }}>
        <button 
          onClick={addTestMessage}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#0e639c', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Add Test Message
        </button>
        <button 
          onClick={clearChat}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#d73a49', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Clear Chat
        </button>
        <button 
          onClick={resetChat}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#28a745', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Reset Chat
        </button>
      </div>

      {/* Info Panel */}
      <div style={{ display: 'flex', height: 'calc(100vh - 120px)' }}>
        <div style={{ 
          width: '300px', 
          backgroundColor: '#252526', 
          borderRight: '1px solid #444',
          padding: '20px',
          overflow: 'auto'
        }}>
          <h3 style={{ marginBottom: '15px', color: '#4FC3F7' }}>Test Information</h3>
          
          <div style={{ marginBottom: '15px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#FFD700' }}>Available Actions:</h4>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: '#ccc' }}>
              <li>Right-click any message for context menu</li>
              <li>Copy message content</li>
              <li>Edit message (mock)</li>
              <li>Delete message</li>
              <li>Export message</li>
              <li>Analyze sentiment (custom)</li>
              <li>Translate message (custom)</li>
              <li>Save as note (custom)</li>
            </ul>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#FFD700' }}>Session Actions:</h4>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: '#ccc' }}>
              <li>Right-click empty space for session menu</li>
              <li>Export entire chat session</li>
              <li>Clear session history</li>
              <li>Session analytics</li>
            </ul>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#FFD700' }}>Test Output:</h4>
            <div style={{ 
              backgroundColor: '#1e1e1e', 
              border: '1px solid #444', 
              borderRadius: '4px',
              padding: '10px',
              maxHeight: '200px',
              overflow: 'auto',
              fontSize: '11px'
            }}>
              {messages.length === 0 ? (
                <div style={{ color: '#666' }}>No actions performed yet...</div>
              ) : (
                messages.map((msg, index) => (
                  <div key={index} style={{ marginBottom: '2px' }}>
                    {msg}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h3 style={{ marginBottom: '20px', color: '#ccc' }}>Chat Messages ({chatMessages.length})</h3>
            
            {chatMessages.length === 0 ? (
              <div 
                style={{ 
                  padding: '40px', 
                  textAlign: 'center', 
                  color: '#666',
                  border: '1px dashed #444',
                  borderRadius: '8px'
                }}
                onContextMenu={(e) => handleContextMenu(e)}
              >
                No messages. Right-click here to access session actions.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {chatMessages.map((message, index) => (
                  <div
                    key={message.id}
                    style={{
                      padding: '15px',
                      backgroundColor: message.sender === 'user' ? '#2d4a6b' : '#2d5a2d',
                      borderRadius: '8px',
                      cursor: 'context-menu',
                      border: selectedMessage?.id === message.id ? '2px solid #4CAF50' : '1px solid #444'
                    }}
                    onContextMenu={(e) => handleContextMenu(e, message)}
                    onClick={() => setSelectedMessage(message)}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <span style={{ 
                        fontWeight: 'bold',
                        color: message.sender === 'user' ? '#87CEEB' : '#90EE90'
                      }}>
                        {message.sender === 'user' ? 'You' : (message.metadata?.agentName || 'AI Assistant')}
                      </span>
                      <span style={{ fontSize: '12px', color: '#999' }}>
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                      {message.content}
                    </div>
                    {message.metadata?.agentType && (
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
                        Agent: {message.metadata.agentType}
                      </div>
                    )}
                  </div>
                ))}
                
                {/* Empty space for session-level context menu */}
                <div 
                  style={{ 
                    height: '60px', 
                    border: '1px dashed #444', 
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#666',
                    fontSize: '14px'
                  }}
                  onContextMenu={(e) => handleContextMenu(e)}
                >
                  Right-click here for session actions
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          schema={contextMenu.schema}
          context={contextMenu.context}
          visible={true}
          position={contextMenu.position}
          onClose={hideContextMenu}
          onItemClick={handleMenuItemClick}
        />
      )}
    </div>
  );
};

export default ICUITest83;
