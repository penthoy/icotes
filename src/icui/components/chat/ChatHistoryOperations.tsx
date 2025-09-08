/**
 * ICUI Chat History Operations
 * 
 * Registers default commands for Chat History session management.
 * Provides the command implementations for chat history context menu actions.
 */

import { globalCommandRegistry } from '../../lib/commandRegistry';
import { ChatHistoryMenuContext, ChatHistorySession } from '../menus/ChatHistoryContextMenu';
import { log } from '../../../services/frontend-logger';
import { confirmService } from '../../services/confirmService';
import { promptService } from '../../services/promptService';

/**
 * Chat History Operations - Default command implementations
 */
export const chatHistoryOperations = {
  
  /**
   * Open a chat session
   */
  async openSession(context: ChatHistoryMenuContext): Promise<void> {
    const { selectedSessions } = context;
    if (selectedSessions.length !== 1) return;
    
    const session = selectedSessions[0];
    log.info('ChatHistoryOperations', 'Opening session', { sessionId: session.id });
    
    // Emit session switch event or call callback
    if (typeof (window as any).chatHistoryCallback?.onSessionSelect === 'function') {
      (window as any).chatHistoryCallback.onSessionSelect(session.id);
    }
  },

  /**
   * Rename a chat session
   */
  async renameSession(context: ChatHistoryMenuContext): Promise<void> {
    const { selectedSessions } = context;
    if (selectedSessions.length !== 1) return;
    
    const session = selectedSessions[0];
    const newName = await promptService.prompt({
      title: 'Rename Session',
      message: 'Enter new session name:',
      initialValue: session.name,
      confirmText: 'Rename'
    });
    
    if (newName && newName.trim() !== session.name) {
      log.info('ChatHistoryOperations', 'Renaming session', { 
        sessionId: session.id, 
        oldName: session.name, 
        newName: newName.trim() 
      });
      
      // Call rename callback or emit event
      if (typeof (window as any).chatHistoryCallback?.onSessionRename === 'function') {
        await (window as any).chatHistoryCallback.onSessionRename(session.id, newName.trim());
      }
    }
  },

  /**
   * Duplicate a chat session
   */
  async duplicateSession(context: ChatHistoryMenuContext): Promise<void> {
    const { selectedSessions } = context;
    if (selectedSessions.length !== 1) return;
    
    const session = selectedSessions[0];
    const duplicateName = `${session.name} (Copy)`;
    
    log.info('ChatHistoryOperations', 'Duplicating session', { 
      sessionId: session.id, 
      duplicateName 
    });
    
    // Call duplicate callback or emit event
    if (typeof (window as any).chatHistoryCallback?.onSessionDuplicate === 'function') {
      await (window as any).chatHistoryCallback.onSessionDuplicate(session.id, duplicateName);
    }
  },

  /**
   * Delete chat sessions
   */
  async deleteSessions(context: ChatHistoryMenuContext): Promise<void> {
    const { selectedSessions } = context;
    if (selectedSessions.length === 0) return;
    
    const sessionNames = selectedSessions.map(s => s.name).join(', ');
    const confirmMessage = selectedSessions.length === 1 
      ? `Are you sure you want to delete the session "${sessionNames}"?`
      : `Are you sure you want to delete ${selectedSessions.length} sessions?`;
    
  if (await confirmService.confirm({ title: 'Delete Sessions', message: confirmMessage, danger: true, confirmText: 'Delete' })) {
      log.info('ChatHistoryOperations', 'Deleting sessions', { 
        sessionIds: selectedSessions.map(s => s.id),
        count: selectedSessions.length
      });
      
      // Call delete callback or emit event
      if (typeof (window as any).chatHistoryCallback?.onSessionsDelete === 'function') {
        await (window as any).chatHistoryCallback.onSessionsDelete(selectedSessions.map(s => s.id));
      }
    }
  },

  /**
   * Export chat sessions
   */
  async exportSessions(context: ChatHistoryMenuContext): Promise<void> {
    const { selectedSessions } = context;
    if (selectedSessions.length === 0) return;
    
    log.info('ChatHistoryOperations', 'Exporting sessions', { 
      sessionIds: selectedSessions.map(s => s.id),
      count: selectedSessions.length
    });
    
    // Create export data
    const exportData = {
      exportDate: new Date().toISOString(),
      sessions: selectedSessions.map(session => ({
        id: session.id,
        name: session.name,
        updated: session.updated,
        messageCount: session.messageCount || 0
      }))
    };
    
    // Download as JSON file
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedSessions.length === 1 
      ? `chat-session-${selectedSessions[0].name.replace(/[^a-zA-Z0-9]/g, '-')}.json`
      : `chat-sessions-${selectedSessions.length}-sessions.json`;
    a.click();
    URL.revokeObjectURL(url);
  },

  /**
   * Create new chat session
   */
  async newSession(context: ChatHistoryMenuContext): Promise<void> {
    log.info('ChatHistoryOperations', 'Creating new session');
    
    // Call new session callback or emit event
    if (typeof (window as any).chatHistoryCallback?.onSessionCreate === 'function') {
      await (window as any).chatHistoryCallback.onSessionCreate('New Chat');
    }
  },

  /**
   * Refresh sessions list
   */
  async refreshSessions(context: ChatHistoryMenuContext): Promise<void> {
    log.info('ChatHistoryOperations', 'Refreshing sessions');
    
    // Call refresh callback or emit event
    if (typeof (window as any).chatHistoryCallback?.onSessionsRefresh === 'function') {
      await (window as any).chatHistoryCallback.onSessionsRefresh();
    }
  },

  /**
   * Select all sessions
   */
  async selectAllSessions(context: ChatHistoryMenuContext): Promise<void> {
    log.info('ChatHistoryOperations', 'Selecting all sessions');
    
    // Call select all callback or emit event
    if (typeof (window as any).chatHistoryCallback?.onSelectAll === 'function') {
      await (window as any).chatHistoryCallback.onSelectAll();
    }
  },

  /**
   * Clear all sessions
   */
  async clearAllSessions(context: ChatHistoryMenuContext): Promise<void> {
    const { totalSessions } = context;
    
  const confirmMessage = `Are you sure you want to delete all ${totalSessions} chat sessions? This action cannot be undone.`;
  if (await confirmService.confirm({ title: 'Clear All Sessions', message: confirmMessage, danger: true, confirmText: 'Delete All' })) {
      log.info('ChatHistoryOperations', 'Clearing all sessions', { totalSessions });
      
      // Call clear all callback or emit event
      if (typeof (window as any).chatHistoryCallback?.onClearAll === 'function') {
        await (window as any).chatHistoryCallback.onClearAll();
      }
    }
  }
};

/**
 * Register all default Chat History commands
 */
export function registerChatHistoryCommands(): void {
  const commands = [
    {
      id: 'chatHistory.open',
      label: 'Open Session',
      handler: chatHistoryOperations.openSession,
      description: 'Open the selected chat session',
    },
    {
      id: 'chatHistory.rename',
      label: 'Rename',
      handler: chatHistoryOperations.renameSession,
      description: 'Rename the selected chat session',
    },
    {
      id: 'chatHistory.duplicate',
      label: 'Duplicate Session',
      handler: chatHistoryOperations.duplicateSession,
      description: 'Create a copy of the selected chat session',
    },
    {
      id: 'chatHistory.delete',
      label: 'Delete',
      handler: chatHistoryOperations.deleteSessions,
      description: 'Delete the selected chat sessions',
    },
    {
      id: 'chatHistory.export',
      label: 'Export',
      handler: chatHistoryOperations.exportSessions,
      description: 'Export chat sessions to JSON file',
    },
    {
      id: 'chatHistory.newSession',
      label: 'New Session',
      handler: chatHistoryOperations.newSession,
      description: 'Create a new chat session',
    },
    {
      id: 'chatHistory.refresh',
      label: 'Refresh',
      handler: chatHistoryOperations.refreshSessions,
      description: 'Refresh the chat sessions list',
    },
    {
      id: 'chatHistory.selectAll',
      label: 'Select All',
      handler: chatHistoryOperations.selectAllSessions,
      description: 'Select all chat sessions',
    },
    {
      id: 'chatHistory.clearAll',
      label: 'Clear All',
      handler: chatHistoryOperations.clearAllSessions,
      description: 'Delete all chat sessions',
    },
  ];

  commands.forEach(command => {
    globalCommandRegistry.register({
      id: command.id,
      label: command.label,
      description: command.description,
      handler: command.handler,
    });
  });

  log.info('ChatHistoryOperations', 'Registered chat history commands', { 
    count: commands.length,
    commands: commands.map(c => c.id)
  });
}

/**
 * Unregister all Chat History commands
 */
export function unregisterChatHistoryCommands(): void {
  const commandIds = [
    'chatHistory.open',
    'chatHistory.rename',
    'chatHistory.duplicate',
    'chatHistory.delete',
    'chatHistory.export',
    'chatHistory.newSession',
    'chatHistory.refresh',
    'chatHistory.selectAll',
    'chatHistory.clearAll',
  ];

  commandIds.forEach(id => {
    globalCommandRegistry.unregister(id);
  });

  log.info('ChatHistoryOperations', 'Unregistered chat history commands', { 
    count: commandIds.length 
  });
}
