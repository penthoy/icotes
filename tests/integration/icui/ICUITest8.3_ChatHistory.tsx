/**
 * ICUI Test 8.3 - Chat History Session Context Menus
 * 
 * Tests Step 8.3: Chat History session context menus with multi-select support,
 * session management actions, and extensibility.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { 
  createChatHistoryContextMenu, 
  handleChatHistoryContextMenuClick, 
  ChatHistoryMenuContext,
  ChatHistoryMenuExtensions,
  registerChatHistoryCommand,
  createCustomChatHistoryMenuGroup,
  ChatHistorySession
} from '../../../src/icui/components/menus/ChatHistoryContextMenu';
import { registerChatHistoryCommands } from '../../../src/icui/components/chat/ChatHistoryOperations';
import { ContextMenu } from '../../../src/icui/components/ui/ContextMenu';
import { MenuSchema, MenuContext, MenuItem } from '../../../src/icui/lib/menuSchemas';
import { globalCommandRegistry } from '../../../src/icui/lib/commandRegistry';
import { log } from '../../../src/services/frontend-logger';

/**
 * Mock chat history sessions for testing
 */
const mockSessions: ChatHistorySession[] = [
  {
    id: 'session-1',
    name: 'React Components Discussion',
    updated: Date.now() - 30000,
    messageCount: 15
  },
  {
    id: 'session-2', 
    name: 'TypeScript Help',
    updated: Date.now() - 120000,
    messageCount: 8
  },
  {
    id: 'session-3',
    name: 'Project Planning',
    updated: Date.now() - 300000,
    messageCount: 23
  },
  {
    id: 'session-4',
    name: 'Code Review Session',
    updated: Date.now() - 600000,
    messageCount: 12
  },
  {
    id: 'session-5',
    name: 'Bug Investigation',
    updated: Date.now() - 900000,
    messageCount: 7
  }
];

/**
 * Register custom chat history commands for testing
 */
const registerCustomChatHistoryCommands = () => {
  // Custom command: Archive sessions
  registerChatHistoryCommand(
    'chatHistory.archive',
    'Archive Sessions',
    async (context: ChatHistoryMenuContext) => {
      const { selectedSessions } = context;
      if (selectedSessions.length === 0) return;
      
      const sessionNames = selectedSessions.map(s => s.name).join(', ');
      alert(`Archived ${selectedSessions.length} session(s):\n${sessionNames}`);
      log.info('CustomChatHistoryCommand', 'Archived sessions', { 
        sessionIds: selectedSessions.map(s => s.id),
        count: selectedSessions.length
      });
    },
    {
      icon: '📦',
      description: 'Archive the selected chat sessions',
    }
  );

  // Custom command: Analyze session statistics
  registerChatHistoryCommand(
    'chatHistory.analyze',
    'Analyze Sessions',
    async (context: ChatHistoryMenuContext) => {
      const { selectedSessions } = context;
      if (selectedSessions.length === 0) return;
      
      const totalMessages = selectedSessions.reduce((sum, s) => sum + (s.messageCount || 0), 0);
      const avgMessages = Math.round(totalMessages / selectedSessions.length);
      const oldestSession = selectedSessions.reduce((oldest, s) => 
        s.updated < oldest.updated ? s : oldest
      );
      
      alert(`Session Analysis:\n\nSessions: ${selectedSessions.length}\nTotal Messages: ${totalMessages}\nAverage Messages: ${avgMessages}\nOldest Session: ${oldestSession.name}\nLast Updated: ${new Date(oldestSession.updated).toLocaleString()}`);
      log.info('CustomChatHistoryCommand', 'Analyzed sessions', { 
        sessionCount: selectedSessions.length,
        totalMessages,
        avgMessages
      });
    },
    {
      icon: '📊',
      description: 'Analyze statistics for the selected sessions',
    }
  );

  // Custom command: Share sessions
  registerChatHistoryCommand(
    'chatHistory.share',
    'Share Sessions',
    async (context: ChatHistoryMenuContext) => {
      const { selectedSessions } = context;
      if (selectedSessions.length === 0) return;
      
      const shareData = selectedSessions.map(s => ({
        name: s.name,
        messageCount: s.messageCount,
        lastUpdated: new Date(s.updated).toISOString()
      }));
      
      // Mock share functionality
      const shareUrl = `https://example.com/shared-sessions/${Date.now()}`;
      alert(`Sessions shared successfully!\n\nShare URL: ${shareUrl}\n\nSessions:\n${shareData.map(s => `• ${s.name} (${s.messageCount} messages)`).join('\n')}`);
      log.info('CustomChatHistoryCommand', 'Shared sessions', { 
        sessionIds: selectedSessions.map(s => s.id),
        shareUrl
      });
    },
    {
      icon: '🔗',
      description: 'Share the selected chat sessions',
    }
  );
};

interface ContextMenuState {
  schema: MenuSchema;
  context: MenuContext;
  position: { x: number; y: number };
}

const ICUITest83Fixed: React.FC = () => {
  const [messages, setMessages] = useState<string[]>([]);
  const [sessions, setSessions] = useState<ChatHistorySession[]>(mockSessions);
  const [selectedSessions, setSelectedSessions] = useState<ChatHistorySession[]>([]);
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

  // Setup global callbacks for session operations
  useEffect(() => {
    // Setup global callbacks that the operations can call
    (window as any).chatHistoryCallback = {
      onSessionSelect: (sessionId: string) => {
        const session = sessions.find(s => s.id === sessionId);
        addMessage(`Opened session: ${session?.name || sessionId}`);
      },
      onSessionRename: async (sessionId: string, newName: string) => {
        setSessions(prev => prev.map(s => 
          s.id === sessionId ? { ...s, name: newName } : s
        ));
        addMessage(`Renamed session to: ${newName}`);
      },
      onSessionDuplicate: async (sessionId: string, duplicateName: string) => {
        const originalSession = sessions.find(s => s.id === sessionId);
        if (originalSession) {
          const newSession: ChatHistorySession = {
            ...originalSession,
            id: `session-${Date.now()}`,
            name: duplicateName,
            updated: Date.now()
          };
          setSessions(prev => [newSession, ...prev]);
          addMessage(`Duplicated session: ${duplicateName}`);
        }
      },
      onSessionsDelete: async (sessionIds: string[]) => {
        setSessions(prev => prev.filter(s => !sessionIds.includes(s.id)));
        setSelectedSessions(prev => prev.filter(s => !sessionIds.includes(s.id)));
        addMessage(`Deleted ${sessionIds.length} session(s)`);
      },
      onSessionCreate: async (name: string) => {
        const newSession: ChatHistorySession = {
          id: `session-${Date.now()}`,
          name,
          updated: Date.now(),
          messageCount: 0
        };
        setSessions(prev => [newSession, ...prev]);
        addMessage(`Created new session: ${name}`);
      },
      onSessionsRefresh: async () => {
        addMessage('Refreshed sessions list');
      },
      onSelectAll: async () => {
        setSelectedSessions([...sessions]);
        addMessage(`Selected all ${sessions.length} sessions`);
      },
      onClearAll: async () => {
        setSessions([]);
        setSelectedSessions([]);
        addMessage('Cleared all sessions');
      }
    };

    return () => {
      delete (window as any).chatHistoryCallback;
    };
  }, [sessions]);

  useEffect(() => {
    // Register default and custom commands when component mounts
    registerChatHistoryCommands();
    registerCustomChatHistoryCommands();
    log.info('ICUITest8.3', 'Registered Chat History commands');
    
    return () => {
      // Cleanup: Unregister custom commands when component unmounts
      ['chatHistory.archive', 'chatHistory.analyze', 'chatHistory.share'].forEach(commandId => {
        globalCommandRegistry.unregister(commandId);
      });
      log.info('ICUITest8.3', 'Unregistered custom Chat History commands');
    };
  }, []);

  const handleSessionClick = useCallback((session: ChatHistorySession, event: React.MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      // Multi-select with Ctrl/Cmd
      setSelectedSessions(prev => {
        const isSelected = prev.some(s => s.id === session.id);
        if (isSelected) {
          return prev.filter(s => s.id !== session.id);
        } else {
          return [...prev, session];
        }
      });
    } else if (event.shiftKey && selectedSessions.length > 0) {
      // Range select with Shift
      const lastSelected = selectedSessions[selectedSessions.length - 1];
      const lastIndex = sessions.findIndex(s => s.id === lastSelected.id);
      const currentIndex = sessions.findIndex(s => s.id === session.id);
      
      const startIndex = Math.min(lastIndex, currentIndex);
      const endIndex = Math.max(lastIndex, currentIndex);
      
      const rangeSelected = sessions.slice(startIndex, endIndex + 1);
      setSelectedSessions(rangeSelected);
    } else {
      // Single select
      setSelectedSessions([session]);
    }
  }, [selectedSessions, sessions]);

  const handleContextMenu = useCallback((event: React.MouseEvent, session?: ChatHistorySession) => {
    event.preventDefault();
    event.stopPropagation();

    // If right-clicking on a session that's not selected, select only that session
    let contextSessions = selectedSessions;
    if (session && !selectedSessions.some(s => s.id === session.id)) {
      contextSessions = [session];
      setSelectedSessions([session]);
    }

    // Create menu context
    const menuContext: ChatHistoryMenuContext = {
      panelType: 'chatHistory',
      selectedSessions: contextSessions,
      totalSessions: sessions.length,
      canRename: true,
      canDelete: true,
      canDuplicate: true,
      canExport: true,
    };

    // Create menu extensions for testing
    const extensions: ChatHistoryMenuExtensions = {
      customCommands: [
        'chatHistory.archive',
        'chatHistory.analyze',
        'chatHistory.share'
      ],
      customGroups: [
        createCustomChatHistoryMenuGroup('management', [
          { id: 'chatHistory.archive', label: 'Archive Sessions', icon: '📦' }
        ], { 
          label: 'Session Management',
          separator: true
        }),
        createCustomChatHistoryMenuGroup('analytics', [
          { id: 'chatHistory.analyze', label: 'Analyze Sessions', icon: '📊' },
          { id: 'chatHistory.share', label: 'Share Sessions', icon: '🔗' }
        ], { 
          label: 'Analytics & Sharing',
          separator: true
        })
      ],
      hiddenItems: [] // Don't hide any items for testing
    };

    const schema = createChatHistoryContextMenu(menuContext, extensions);
    
    showContextMenu(event, schema, menuContext);
  }, [sessions, selectedSessions, showContextMenu]);

  const clearSelection = () => {
    setSelectedSessions([]);
    addMessage('Cleared selection');
  };

  const selectAll = () => {
    setSelectedSessions([...sessions]);
    addMessage(`Selected all ${sessions.length} sessions`);
  };

  const addTestSession = () => {
    const newSession: ChatHistorySession = {
      id: `session-${Date.now()}`,
      name: `Test Session ${sessions.length + 1}`,
      updated: Date.now(),
      messageCount: Math.floor(Math.random() * 20) + 1
    };
    setSessions(prev => [newSession, ...prev]);
    addMessage(`Added test session: ${newSession.name}`);
  };

  const formatRelativeTime = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return new Date(timestamp).toLocaleDateString();
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
          ICUI Test 8.3 - Chat History Session Context Menus
        </h2>
        <p style={{ margin: '0', color: '#ccc', fontSize: '14px' }}>
          Testing extensible context menus for chat history sessions with multi-select support, 
          session management, and custom commands.
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
          onClick={addTestSession}
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
          Add Test Session
        </button>
        <button 
          onClick={selectAll}
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
          Select All
        </button>
        <button 
          onClick={clearSelection}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#6c757d', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Clear Selection
        </button>
        <span style={{ 
          padding: '8px 16px', 
          backgroundColor: '#495057', 
          borderRadius: '4px',
          fontSize: '12px',
          color: '#fff'
        }}>
          Selected: {selectedSessions.length}/{sessions.length}
        </span>
      </div>

      {/* Main Content */}
      <div style={{ display: 'flex', height: 'calc(100vh - 140px)' }}>
        {/* Info Panel */}
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
              <li>Click sessions to select (Ctrl for multi-select)</li>
              <li>Shift+click for range selection</li>
              <li>Right-click sessions for context menu</li>
              <li>Right-click empty space for session actions</li>
              <li>Rename individual sessions</li>
              <li>Delete single or multiple sessions</li>
              <li>Duplicate sessions</li>
              <li>Export sessions to JSON</li>
              <li>Archive sessions (custom)</li>
              <li>Analyze session statistics (custom)</li>
              <li>Share sessions (custom)</li>
            </ul>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#FFD700' }}>Multi-Select Support:</h4>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: '#ccc' }}>
              <li>Ctrl+Click: Toggle individual sessions</li>
              <li>Shift+Click: Select range of sessions</li>
              <li>Bulk operations on multiple sessions</li>
              <li>Context menu adapts to selection</li>
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
      
        {/* Chat History Panel */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
          <div style={{ maxWidth: '600px', margin: '0 auto' }}>
            <h3 style={{ marginBottom: '20px', color: '#ccc' }}>
              Chat History Sessions ({sessions.length})
            </h3>
            
            {sessions.length === 0 ? (
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
                No sessions. Right-click here to create a new session.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    style={{
                      padding: '15px',
                      backgroundColor: selectedSessions.some(s => s.id === session.id) 
                        ? '#2d4a6b' 
                        : '#2d2d30',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      border: selectedSessions.some(s => s.id === session.id) 
                        ? '2px solid #4CAF50' 
                        : '1px solid #444',
                      transition: 'all 0.2s ease'
                    }}
                    onClick={(e) => handleSessionClick(session, e)}
                    onContextMenu={(e) => handleContextMenu(e, session)}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <span style={{ 
                        fontWeight: 'bold',
                        color: '#87CEEB',
                        fontSize: '14px'
                      }}>
                        {session.name}
                      </span>
                      <span style={{ fontSize: '12px', color: '#999' }}>
                        {formatRelativeTime(session.updated)}
                      </span>
                    </div>
                    <div style={{ 
                      fontSize: '12px', 
                      color: '#aaa',
                      display: 'flex',
                      justifyContent: 'space-between'
                    }}>
                      <span>Session ID: {session.id}</span>
                      <span>{session.messageCount || 0} messages</span>
                    </div>
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
                    fontSize: '14px',
                    marginTop: '10px'
                  }}
                  onContextMenu={(e) => handleContextMenu(e)}
                >
                  Right-click here for session management actions
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

export default ICUITest83Fixed;
