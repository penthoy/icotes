import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useChatHistory } from '../../hooks/useChatHistory';
import { useChatSessionSync } from '../../hooks/useChatSessionSync';
import { Trash2, Edit3, Plus, MessageSquare, Clock, Search, Copy } from 'lucide-react';
import { ContextMenu, useContextMenu } from '../ui/ContextMenu';
import { createChatHistoryContextMenu, handleChatHistoryContextMenuClick, ChatHistoryMenuContext } from '../menus/ChatHistoryContextMenu';
import { registerChatHistoryCommands } from '../chat/ChatHistoryOperations';
import { confirmService } from '../../services/confirmService';
import { promptService } from '../../services/promptService';

interface ICUIChatHistoryProps {
  className?: string;
  onSessionSelect?: (sessionId: string) => void;
}

const ICUIChatHistory: React.FC<ICUIChatHistoryProps> = ({ 
  className = '', 
  onSessionSelect 
}) => {
  const { 
    sessions, 
    activeSessionId, 
    createSession, 
    switchSession, 
    renameSession, 
    deleteSession,
    refreshSessions 
  } = useChatHistory();
  
  const [editingId, setEditingId] = useState<string>('');
  const [tempName, setTempName] = useState<string>('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  // Multi-select state
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set());
  const lastSelectedRef = useRef<string | null>(null);
  
  // Context menu hook
  const { contextMenu, showContextMenu, hideContextMenu } = useContextMenu();

  // Session synchronization
  const { emitSessionChange, onSessionChange } = useChatSessionSync('ICUIChatHistory');

  // Register commands on mount (only once)
  useEffect(() => {
    registerChatHistoryCommands();
    
    return () => {
      delete (window as any).chatHistoryCallback;
    };
  }, []); // Empty dependency array - register commands only once on mount

  // Setup global callbacks for command operations (updates when dependencies change)
  useEffect(() => {
    (window as any).chatHistoryCallback = {
      onSessionSelect: (sessionId: string) => {
        handleSelect(sessionId);
      },
      onSessionRename: async (sessionId: string, newName: string) => {
        await renameSession(sessionId, newName);
        setEditingId('');
        setTempName('');
      },
      onSessionDuplicate: async (sessionId: string, duplicateName: string) => {
        const newSessionId = await createSession(duplicateName);
        emitSessionChange(newSessionId, 'create', duplicateName);
        onSessionSelect?.(newSessionId);
      },
      onSessionsDelete: async (sessionIds: string[]) => {
        for (const sessionId of sessionIds) {
          await deleteSession(sessionId);
        }
        setSelectedSessions(new Set());
        setShowDeleteConfirm('');
      },
      onSessionCreate: async (name: string) => {
        const newSessionId = await createSession(name);
        emitSessionChange(newSessionId, 'create', name);
        onSessionSelect?.(newSessionId);
      },
      onSessionsRefresh: async () => {
        await refreshSessions();
      },
      onSelectAll: () => {
        setSelectedSessions(new Set(sessions.map(s => s.id)));
      },
      onClearAll: async () => {
        for (const session of sessions) {
          await deleteSession(session.id);
        }
        setSelectedSessions(new Set());
      }
    };
  }, [sessions, createSession, renameSession, deleteSession, refreshSessions, emitSessionChange, onSessionSelect]);

  // Keep ChatHistory in sync when other components (e.g., ICUIChat) create/delete/switch sessions
  useEffect(() => {
    return onSessionChange((sessionId, action) => {
      if (action === 'create' || action === 'delete') {
        // Refresh list from backend to include the new/removed session
        refreshSessions();
      } else if (action === 'switch') {
        // Mirror active highlight
        if (sessionId !== activeSessionId) {
          switchSession(sessionId);
        }
      }
    });
  }, [onSessionChange, refreshSessions, switchSession, activeSessionId]);

  // Filter and sort sessions based on search query
  const filteredAndSortedSessions = useMemo(() => {
    let filtered = sessions;
    
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = sessions.filter(session => 
        (session.name || 'Untitled').toLowerCase().includes(query)
      );
    }
    
    return filtered.slice().sort((a, b) => b.updated - a.updated);
  }, [sessions, searchQuery]);

  // Session management handlers
  const handleCreateNew = useCallback(async () => {
    try {
      const newSessionId = await createSession('New Chat');
      emitSessionChange(newSessionId, 'create', 'New Chat');
      onSessionSelect?.(newSessionId);
    } catch (error) {
      console.error('Failed to create new chat session:', error);
    }
  }, [createSession, emitSessionChange, onSessionSelect]);

  // Multi-select helpers
  const handleSessionClick = useCallback((sessionId: string, event: React.MouseEvent) => {
    if (editingId) return; // Don't interfere with rename mode
    
    if (event.ctrlKey || event.metaKey) {
      // Ctrl+click: toggle selection
      setSelectedSessions(prev => {
        const newSet = new Set(prev);
        if (newSet.has(sessionId)) {
          newSet.delete(sessionId);
        } else {
          newSet.add(sessionId);
        }
        return newSet;
      });
      lastSelectedRef.current = sessionId;
    } else if (event.shiftKey && lastSelectedRef.current) {
      // Shift+click: range selection
      const currentIndex = filteredAndSortedSessions.findIndex(s => s.id === sessionId);
      const lastIndex = filteredAndSortedSessions.findIndex(s => s.id === lastSelectedRef.current);
      
      if (currentIndex !== -1 && lastIndex !== -1) {
        const start = Math.min(currentIndex, lastIndex);
        const end = Math.max(currentIndex, lastIndex);
        const range = filteredAndSortedSessions.slice(start, end + 1).map(s => s.id);
        
        setSelectedSessions(prev => {
          const newSet = new Set(prev);
          range.forEach(id => newSet.add(id));
          return newSet;
        });
      }
    } else {
      // Regular click: clear selection and select/activate this session
      setSelectedSessions(new Set([sessionId]));
      lastSelectedRef.current = sessionId;
      handleSelect(sessionId);
    }
  }, [editingId, filteredAndSortedSessions]);

  const handleSelect = useCallback((sessionId: string) => {
    const selected = sessions.find(s => s.id === sessionId);
    // Always emit a switch and update the store, even if re-selecting the same session.
    // This keeps ICUIChat in sync when it missed prior updates (e.g., on initial mount)
    switchSession(sessionId);
    emitSessionChange(sessionId, 'switch', selected?.name);
    onSessionSelect?.(sessionId);
  }, [sessions, switchSession, emitSessionChange, onSessionSelect]);

  // Context menu handlers
  const handleContextMenu = useCallback((event: React.MouseEvent, sessionId: string) => {
    event.preventDefault();
    event.stopPropagation();
    
    // If right-clicking on a non-selected session, select only that session
    if (!selectedSessions.has(sessionId)) {
      setSelectedSessions(new Set([sessionId]));
      lastSelectedRef.current = sessionId;
    }
    
    // Get selected session objects
    const selectedSessionObjects = sessions.filter(s => selectedSessions.has(s.id) || s.id === sessionId);
    
    const menuContext: ChatHistoryMenuContext = {
      panelType: 'chatHistory',
      selectedSessions: selectedSessionObjects.map(s => ({
        id: s.id,
        name: s.name || 'Untitled',
        updated: s.updated,
        messageCount: 0 // TODO: get actual message count
      })),
      totalSessions: sessions.length,
      canRename: selectedSessionObjects.length === 1,
      canDelete: selectedSessionObjects.length > 0,
      canDuplicate: selectedSessionObjects.length === 1,
      canExport: selectedSessionObjects.length > 0,
    };
    
    const schema = createChatHistoryContextMenu(menuContext);
    showContextMenu(event, schema, menuContext);
  }, [selectedSessions, sessions, showContextMenu]);

  const handleContextMenuItemClick = useCallback((item: any) => {
    const selectedSessionObjects = sessions.filter(s => selectedSessions.has(s.id));
    const menuContext: ChatHistoryMenuContext = {
      panelType: 'chatHistory',
      selectedSessions: selectedSessionObjects.map(s => ({
        id: s.id,
        name: s.name || 'Untitled',
        updated: s.updated,
        messageCount: 0
      })),
      totalSessions: sessions.length,
      canRename: selectedSessionObjects.length === 1,
      canDelete: selectedSessionObjects.length > 0,
      canDuplicate: selectedSessionObjects.length === 1,
      canExport: selectedSessionObjects.length > 0,
    };
    
    handleChatHistoryContextMenuClick(item, menuContext);
    hideContextMenu();
  }, [selectedSessions, sessions, hideContextMenu]);

  // Inline rename (VS Code style)
  const handleSessionDoubleClick = useCallback((sessionId: string, event: React.MouseEvent) => {
    if (selectedSessions.size === 1 && selectedSessions.has(sessionId)) {
      event.stopPropagation();
      const session = sessions.find(s => s.id === sessionId);
      if (session) {
        setEditingId(sessionId);
        setTempName(session.name || 'Untitled');
      }
    }
  }, [selectedSessions, sessions]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (editingId) return; // Don't interfere with rename mode
    
    if (event.key === 'F2' && selectedSessions.size === 1) {
      // F2 to rename
      const sessionId = Array.from(selectedSessions)[0];
      const session = sessions.find(s => s.id === sessionId);
      if (session) {
        setEditingId(sessionId);
        setTempName(session.name || 'Untitled');
      }
    } else if (event.key === 'Delete' && selectedSessions.size > 0) {
      // Delete key to delete selected sessions
      const selectedSessionObjects = sessions.filter(s => selectedSessions.has(s.id));
      const sessionNames = selectedSessionObjects.map(s => s.name || 'Untitled').join(', ');
      const confirmMessage = selectedSessionObjects.length === 1 
        ? `Are you sure you want to delete the session "${sessionNames}"?`
        : `Are you sure you want to delete ${selectedSessionObjects.length} sessions?`;
      
      (async () => {
        const ok = await confirmService.confirm({ title: 'Delete Sessions', message: confirmMessage, danger: true, confirmText: 'Delete' });
        if (ok) {
          selectedSessionObjects.forEach(session => {
            deleteSession(session.id);
          });
          setSelectedSessions(new Set());
        }
      })();
    } else if (event.ctrlKey && event.key === 'a') {
      // Ctrl+A to select all
      event.preventDefault();
      setSelectedSessions(new Set(sessions.map(s => s.id)));
    }
  }, [editingId, selectedSessions, sessions, deleteSession]);

  const handleStartRename = useCallback((session: any, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(session.id);
    setTempName(session.name || 'Untitled');
  }, []);

  const handleSaveRename = useCallback(async (sessionId: string) => {
    if (tempName.trim()) {
      try {
        await renameSession(sessionId, tempName.trim());
      } catch (error) {
        console.error('Failed to rename session:', error);
      }
    }
    setEditingId('');
    setTempName('');
  }, [renameSession, tempName]);

  const handleCancelRename = useCallback(() => {
    setEditingId('');
    setTempName('');
  }, []);

  const handleDeleteClick = useCallback((sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteConfirm(sessionId);
  }, []);

  const handleConfirmDelete = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
      setShowDeleteConfirm('');
    } catch (error) {
      console.error('Failed to delete session:', error);
      setShowDeleteConfirm('');
    }
  }, [deleteSession]);

  const formatRelativeTime = useCallback((timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return new Date(timestamp).toLocaleDateString();
  }, []);

  return (
    <div 
      className={`flex flex-col h-full ${className}`}
      style={{ backgroundColor: 'var(--icui-bg-primary)' }}
      onKeyDown={handleKeyDown}
      onClick={(e) => {
        // Deselect all when clicking on empty space (not on a session card or input)
        const target = e.target as HTMLElement;
        if (!target.closest('.icui-chat-session-card') && !target.closest('input,textarea,button,[role="menu"]')) {
          setSelectedSessions(new Set());
          lastSelectedRef.current = null;
        }
      }}
      tabIndex={-1}
    >
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 border-b"
        style={{ borderBottomColor: 'var(--icui-border-subtle)' }}
      >
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5" style={{ color: 'var(--icui-text-primary)' }} />
          <h2 className="text-lg font-semibold" style={{ color: 'var(--icui-text-primary)' }}>
            Chat History
          </h2>
          {selectedSessions.size > 0 && (
            <span className="text-sm px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}>
              {selectedSessions.size} selected
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {selectedSessions.size > 0 && (
            <>
              {selectedSessions.size === 1 && (
                <button
                  onClick={() => {
                    const sessionId = Array.from(selectedSessions)[0];
                    const session = sessions.find(s => s.id === sessionId);
                    if (session) {
                      setEditingId(sessionId);
                      setTempName(session.name || 'Untitled');
                    }
                  }}
                  className="p-2 rounded hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: 'var(--icui-bg-secondary)', color: 'var(--icui-text-primary)' }}
                  title="Rename session (F2)"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
              )}
              
              {selectedSessions.size === 1 && (
                <button
                  onClick={async () => {
                    const sessionId = Array.from(selectedSessions)[0];
                    const session = sessions.find(s => s.id === sessionId);
                    if (session) {
                      const duplicateName = `${session.name || 'Untitled'} (Copy)`;
                      const newSessionId = await createSession(duplicateName);
                      emitSessionChange(newSessionId, 'create', duplicateName);
                      onSessionSelect?.(newSessionId);
                    }
                  }}
                  className="p-2 rounded hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: 'var(--icui-bg-secondary)', color: 'var(--icui-text-primary)' }}
                  title="Duplicate session"
                >
                  <Copy className="w-4 h-4" />
                </button>
              )}
              
              <button
                onClick={() => {
                  const selectedSessionObjects = sessions.filter(s => selectedSessions.has(s.id));
                  const sessionNames = selectedSessionObjects.map(s => s.name || 'Untitled').join(', ');
                  const confirmMessage = selectedSessionObjects.length === 1 
                    ? `Are you sure you want to delete the session "${sessionNames}"?`
                    : `Are you sure you want to delete ${selectedSessionObjects.length} sessions?`;
                  
                  (async () => {
                    const ok = await confirmService.confirm({ title: 'Delete Sessions', message: confirmMessage, danger: true, confirmText: 'Delete' });
                    if (ok) {
                      selectedSessionObjects.forEach(session => {
                        deleteSession(session.id);
                      });
                      setSelectedSessions(new Set());
                    }
                  })();
                }}
                className="p-2 rounded hover:opacity-80 transition-opacity"
                style={{ backgroundColor: 'var(--icui-text-error)', color: 'white' }}
                title="Delete selected sessions (Delete)"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
          
          <button
            onClick={handleCreateNew}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-md text-sm hover:opacity-80 transition-opacity"
            style={{ 
              backgroundColor: 'var(--icui-accent)', 
              color: 'var(--icui-text-primary)' 
            }}
            title="Create new chat session"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-4 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" style={{ color: 'var(--icui-text-secondary)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chat sessions..."
            className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border outline-none transition-colors"
            style={{
              backgroundColor: 'var(--icui-bg-secondary)',
              borderColor: 'var(--icui-border-subtle)',
              color: 'var(--icui-text-primary)'
            }}
          />
        </div>
        {searchQuery && (
          <div className="mt-2 text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
            {filteredAndSortedSessions.length} session{filteredAndSortedSessions.length === 1 ? '' : 's'} found
          </div>
        )}
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-2">
        {filteredAndSortedSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            {searchQuery ? (
              <>
                <Search 
                  className="w-12 h-12 mb-4 opacity-50" 
                  style={{ color: 'var(--icui-text-muted)' }} 
                />
                <p className="text-sm mb-2" style={{ color: 'var(--icui-text-muted)' }}>
                  No sessions match "{searchQuery}"
                </p>
                <p className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                  Try a different search term
                </p>
              </>
            ) : (
              <>
                <MessageSquare 
                  className="w-12 h-12 mb-4 opacity-50" 
                  style={{ color: 'var(--icui-text-muted)' }} 
                />
                <p className="text-sm mb-2" style={{ color: 'var(--icui-text-muted)' }}>
                  No chat sessions yet
                </p>
                <p className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
                  Create your first chat to get started
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredAndSortedSessions.map((session) => {
              const isSelected = selectedSessions.has(session.id);
              const isEditing = editingId === session.id;
              
        return (
                <div
                  key={session.id}
                  onClick={(e) => handleSessionClick(session.id, e)}
                  onDoubleClick={(e) => handleSessionDoubleClick(session.id, e)}
                  onContextMenu={(e) => handleContextMenu(e, session.id)}
                  className={`icui-chat-session-card group relative p-3 rounded-lg cursor-pointer transition-all hover:opacity-80 ${
                    isSelected ? 'ring-2' : ''
                  }`}
                  style={{
                    // Two-state styling: deselected (black) and selected (blue ring)
                    backgroundColor: 'var(--icui-bg-secondary)',
                    '--tw-ring-color': isSelected ? 'var(--icui-accent)' : 'transparent'
                  } as React.CSSProperties}
                  title={`Click to select • Right-click for options${isSelected ? ' • F2 to rename • Del to delete' : ''}`}
                >
                  {/* Session Content */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {isEditing ? (
                        <input
                          value={tempName}
                          onChange={(e) => setTempName(e.target.value)}
                          onBlur={() => handleSaveRename(session.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(session.id);
                            if (e.key === 'Escape') handleCancelRename();
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="w-full px-2 py-1 text-sm rounded border bg-transparent outline-none"
                          style={{ 
                            color: 'var(--icui-text-primary)',
                            borderColor: 'var(--icui-border-subtle)'
                          }}
                          autoFocus
                        />
                      ) : (
                        <h3 
                          className="font-medium text-sm truncate mb-1 select-none cursor-text" 
                          style={{ color: 'var(--icui-text-primary)' }}
                          onClick={(e) => {
                            if (selectedSessions.size === 1 && selectedSessions.has(session.id)) {
                              e.stopPropagation();
                              setEditingId(session.id);
                              setTempName(session.name || 'Untitled');
                            }
                          }}
                          title="Click to rename (F2)"
                        >
                          {session.name || 'Untitled Chat'}
                        </h3>
                      )}
                      
                      <div className="flex items-center space-x-2 text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
                        <Clock className="w-3 h-3" />
                        <span>{formatRelativeTime(session.updated)}</span>
                      </div>
                    </div>

                    {/* Per-item hover actions removed to simplify UI */}
                  </div>

                  {/* Delete Confirmation */}
                  {showDeleteConfirm === session.id && (
                    <div 
                      className="absolute inset-0 flex items-center justify-center rounded-lg"
                      style={{ backgroundColor: 'var(--icui-bg-primary)' }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="text-center">
                        <p className="text-xs mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                          Delete this chat?
                        </p>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleConfirmDelete(session.id)}
                            className="px-2 py-1 text-xs rounded"
                            style={{ 
                              backgroundColor: 'var(--icui-text-error)', 
                              color: 'white' 
                            }}
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => setShowDeleteConfirm('')}
                            className="px-2 py-1 text-xs rounded border"
                            style={{ 
                              borderColor: 'var(--icui-border-subtle)',
                              color: 'var(--icui-text-primary)'
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div 
        className="p-3 border-t text-xs"
        style={{ 
          borderTopColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-secondary)'
        }}
      >
        <div className="text-center mb-1">
          {sessions.length === 0 
            ? 'No sessions' 
            : selectedSessions.size > 0
              ? `${selectedSessions.size} of ${sessions.length} session${sessions.length === 1 ? '' : 's'} selected`
              : `${sessions.length} session${sessions.length === 1 ? '' : 's'}`
          }
        </div>
        {selectedSessions.size > 0 && (
          <div className="text-center text-[10px] opacity-70">
            F2: Rename • Del: Delete • Ctrl+A: Select All • Right-click: More options
          </div>
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          schema={contextMenu.schema}
          context={contextMenu.context}
          visible={true}
          position={contextMenu.position}
          onClose={hideContextMenu}
          onItemClick={handleContextMenuItemClick}
        />
      )}
    </div>
  );
};

export default ICUIChatHistory; 