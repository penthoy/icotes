import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useChatHistory } from '../../hooks/useChatHistory';
import { useChatSessionSync } from '../../hooks/useChatSessionSync';
import { Trash2, Edit3, Plus, MessageSquare, Clock, Search } from 'lucide-react';

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

  // Session synchronization
  const { emitSessionChange, onSessionChange } = useChatSessionSync('ICUIChatHistory');

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

  const handleCreateNew = useCallback(async () => {
    try {
      const newSessionId = await createSession('New Chat');
      emitSessionChange(newSessionId, 'create', 'New Chat');
      onSessionSelect?.(newSessionId);
    } catch (error) {
      console.error('Failed to create new chat session:', error);
    }
  }, [createSession, emitSessionChange, onSessionSelect]);

  const handleSelect = useCallback((sessionId: string) => {
    const selected = sessions.find(s => s.id === sessionId);
    if (sessionId !== activeSessionId) {
      switchSession(sessionId);
      emitSessionChange(sessionId, 'switch', selected?.name);
    }
    onSessionSelect?.(sessionId);
  }, [sessions, activeSessionId, switchSession, emitSessionChange, onSessionSelect]);

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
        </div>
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
            {filteredAndSortedSessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelect(session.id)}
                className={`group relative p-3 rounded-lg cursor-pointer transition-all hover:opacity-80 ${
                  session.id === activeSessionId ? 'ring-2' : ''
                }`}
                                 style={{
                   backgroundColor: session.id === activeSessionId 
                     ? 'var(--icui-bg-tertiary)' 
                     : 'var(--icui-bg-secondary)',
                   '--tw-ring-color': session.id === activeSessionId 
                     ? 'var(--icui-accent)' 
                     : 'transparent'
                 } as React.CSSProperties}
              >
                {/* Session Content */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    {editingId === session.id ? (
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
                        className="font-medium text-sm truncate mb-1" 
                        style={{ color: 'var(--icui-text-primary)' }}
                      >
                        {session.name || 'Untitled Chat'}
                      </h3>
                    )}
                    
                    <div className="flex items-center space-x-2 text-xs" style={{ color: 'var(--icui-text-secondary)' }}>
                      <Clock className="w-3 h-3" />
                      <span>{formatRelativeTime(session.updated)}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => handleStartRename(session, e)}
                      className="p-1 rounded hover:bg-opacity-80 transition-colors"
                      style={{ backgroundColor: 'var(--icui-bg-primary)' }}
                      title="Rename session"
                    >
                      <Edit3 className="w-3 h-3" style={{ color: 'var(--icui-text-secondary)' }} />
                    </button>
                    <button
                      onClick={(e) => handleDeleteClick(session.id, e)}
                      className="p-1 rounded hover:bg-opacity-80 transition-colors"
                      style={{ backgroundColor: 'var(--icui-bg-primary)' }}
                      title="Delete session"
                    >
                      <Trash2 className="w-3 h-3" style={{ color: 'var(--icui-text-error)' }} />
                    </button>
                  </div>
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
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div 
        className="p-3 border-t text-xs text-center"
        style={{ 
          borderTopColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-secondary)'
        }}
      >
        {sessions.length === 0 
          ? 'No sessions' 
          : `${sessions.length} session${sessions.length === 1 ? '' : 's'}`
        }
      </div>
    </div>
  );
};

export default ICUIChatHistory; 