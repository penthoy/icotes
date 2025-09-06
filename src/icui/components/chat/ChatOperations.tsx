/**
 * ICUI Chat Operations
 * 
 * Provides file operations and command handlers for Chat context menus.
 * Integrates with the global command registry and chat services.
 */

import { globalCommandRegistry, CommandUtils } from '../../lib/commandRegistry';
import { ChatMessage } from '../../types/chatTypes';
import { ChatMenuContext } from '../menus/ChatContextMenu';
import { log } from '../../../services/frontend-logger';

export interface ChatOperationContext extends ChatMenuContext {
  refreshChat?: () => Promise<void>;
  addMessage?: (message: Partial<ChatMessage>) => Promise<void>;
  editMessage?: (messageId: string, newContent: string) => Promise<void>;
  deleteMessage?: (messageId: string) => Promise<void>;
  clearMessages?: () => Promise<void>;
  exportMessages?: () => Promise<string>;
  onSessionRename?: (oldName: string, newName: string) => void;
}

/**
 * Chat Operations Manager
 * Handles all chat-related operations and commands
 */
export class ChatOperations {
  constructor() {
    this.registerCommands();
  }

  /**
   * Register all chat commands
   */
  private registerCommands(): void {
    const commands = [
      // Message operations
      CommandUtils.createWithShortcut(
        'chat.copyMessage',
        'Copy Message',
        'Ctrl+C',
        this.copyMessage.bind(this),
        { 
          category: 'chat',
          icon: '📋',
          description: 'Copy the selected message to clipboard'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.quoteMessage',
        'Quote & Reply',
        '',
        this.quoteMessage.bind(this),
        { 
          category: 'chat',
          icon: '💬',
          description: 'Quote the selected message and start a reply'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.regenerateResponse',
        'Regenerate Response',
        'Ctrl+R',
        this.regenerateResponse.bind(this),
        { 
          category: 'chat',
          icon: '🔄',
          description: 'Regenerate the AI response for this message'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.editMessage',
        'Edit Message',
        'F2',
        this.editMessage.bind(this),
        { 
          category: 'chat',
          icon: '✏️',
          description: 'Edit the selected user message'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.deleteMessage',
        'Delete Message',
        'Delete',
        this.deleteMessage.bind(this),
        { 
          category: 'chat',
          icon: '🗑️',
          description: 'Delete the selected message'
        }
      ),

      // Session operations
      CommandUtils.createWithShortcut(
        'chat.newSession',
        'New Chat Session',
        'Ctrl+N',
        this.newSession.bind(this),
        { 
          category: 'chat',
          icon: '➕',
          description: 'Start a new chat session'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.renameSession',
        'Rename Session',
        'F2',
        this.renameSession.bind(this),
        { 
          category: 'chat',
          icon: '✏️',
          description: 'Rename the current chat session'
        }
      ),

      CommandUtils.create(
        'chat.exportSession',
        'Export Session',
        this.exportSession.bind(this),
        { 
          category: 'chat',
          icon: '📤',
          description: 'Export the chat session to a file'
        }
      ),

      CommandUtils.create(
        'chat.duplicateSession',
        'Duplicate Session',
        this.duplicateSession.bind(this),
        { 
          category: 'chat',
          icon: '📄',
          description: 'Create a copy of the current chat session'
        }
      ),

      CommandUtils.createWithShortcut(
        'chat.clearSession',
        'Clear Session',
        'Ctrl+Shift+K',
        this.clearSession.bind(this),
        { 
          category: 'chat',
          icon: '🧹',
          description: 'Clear all messages in the current session'
        }
      ),
    ];

    commands.forEach(command => globalCommandRegistry.register(command));
    log.info('ChatOperations', 'Registered chat commands', { count: commands.length });
  }

  /**
   * Copy message content to clipboard
   */
  private async copyMessage(context?: ChatOperationContext): Promise<void> {
    if (!context?.selectedMessage) {
      log.warn('ChatOperations', 'copyMessage called with no selected message');
      return;
    }

    try {
      await navigator.clipboard.writeText(context.selectedMessage.content);
      log.info('ChatOperations', 'Copied message to clipboard', { 
        messageId: context.selectedMessage.id 
      });
    } catch (error) {
      // Fallback for browsers without clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = context.selectedMessage.content;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      
      log.info('ChatOperations', 'Copied message to clipboard (fallback)', { 
        messageId: context.selectedMessage.id 
      });
    }
  }

  /**
   * Quote message and start a reply
   */
  private async quoteMessage(context?: ChatOperationContext): Promise<void> {
    if (!context?.selectedMessage) {
      log.warn('ChatOperations', 'quoteMessage called with no selected message');
      return;
    }

    const quotedText = `> ${context.selectedMessage.content.replace(/\n/g, '\n> ')}\n\n`;
    
    try {
      // This would typically set the input field value in the chat interface
      console.log('Would quote message:', quotedText);
      log.info('ChatOperations', 'Quoted message', { 
        messageId: context.selectedMessage.id,
        quotedLength: quotedText.length
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to quote message', { 
        messageId: context.selectedMessage.id, 
        error 
      });
      throw error;
    }
  }

  /**
   * Regenerate AI response
   */
  private async regenerateResponse(context?: ChatOperationContext): Promise<void> {
    if (!context?.selectedMessage) {
      log.warn('ChatOperations', 'regenerateResponse called with no selected message');
      return;
    }

    try {
      // This would typically trigger a re-generation of the AI response
      console.log('Would regenerate response for message:', context.selectedMessage.id);
      log.info('ChatOperations', 'Regenerated response', { 
        messageId: context.selectedMessage.id 
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to regenerate response', { 
        messageId: context.selectedMessage.id, 
        error 
      });
      throw error;
    }
  }

  /**
   * Edit user message
   */
  private async editMessage(context?: ChatOperationContext): Promise<void> {
    if (!context?.selectedMessage) {
      log.warn('ChatOperations', 'editMessage called with no selected message');
      return;
    }

    const newContent = prompt('Edit message:', context.selectedMessage.content);
    if (!newContent?.trim() || newContent.trim() === context.selectedMessage.content) {
      return;
    }

    try {
      await context.editMessage?.(context.selectedMessage.id, newContent.trim());
      await context.refreshChat?.();
      log.info('ChatOperations', 'Edited message', { 
        messageId: context.selectedMessage.id 
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to edit message', { 
        messageId: context.selectedMessage.id, 
        error 
      });
      throw error;
    }
  }

  /**
   * Delete message
   */
  private async deleteMessage(context?: ChatOperationContext): Promise<void> {
    if (!context?.selectedMessage) {
      log.warn('ChatOperations', 'deleteMessage called with no selected message');
      return;
    }

    const confirmed = confirm(`Are you sure you want to delete this message?`);
    if (!confirmed) return;

    try {
      await context.deleteMessage?.(context.selectedMessage.id);
      await context.refreshChat?.();
      log.info('ChatOperations', 'Deleted message', { 
        messageId: context.selectedMessage.id 
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to delete message', { 
        messageId: context.selectedMessage.id, 
        error 
      });
      throw error;
    }
  }

  /**
   * Start new chat session
   */
  private async newSession(context?: ChatOperationContext): Promise<void> {
    try {
      // This would typically create a new chat session
      console.log('Would create new chat session');
      log.info('ChatOperations', 'Created new session');
    } catch (error) {
      log.error('ChatOperations', 'Failed to create new session', { error });
      throw error;
    }
  }

  /**
   * Rename chat session
   */
  private async renameSession(context?: ChatOperationContext): Promise<void> {
    const currentName = context?.chatId || 'Untitled';
    const newName = prompt('Enter new session name:', currentName);
    if (!newName?.trim() || newName.trim() === currentName) return;

    try {
      context?.onSessionRename?.(currentName, newName.trim());
      log.info('ChatOperations', 'Renamed session', { 
        oldName: currentName, 
        newName: newName.trim() 
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to rename session', { 
        oldName: currentName, 
        newName: newName.trim(), 
        error 
      });
      throw error;
    }
  }

  /**
   * Export chat session
   */
  private async exportSession(context?: ChatOperationContext): Promise<void> {
    if (!context?.chatMessages?.length) {
      log.warn('ChatOperations', 'exportSession called with no messages');
      return;
    }

    try {
      const exportData = {
        sessionId: context.chatId,
        exportDate: new Date().toISOString(),
        messageCount: context.chatMessages.length,
        messages: context.chatMessages.map(msg => ({
          id: msg.id,
          content: msg.content,
          sender: msg.sender,
          timestamp: msg.timestamp,
          metadata: msg.metadata
        }))
      };

      const exportText = JSON.stringify(exportData, null, 2);
      const blob = new Blob([exportText], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-session-${context.chatId || 'export'}-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      log.info('ChatOperations', 'Exported session', { 
        sessionId: context.chatId,
        messageCount: context.chatMessages.length
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to export session', { error });
      throw error;
    }
  }

  /**
   * Duplicate chat session
   */
  private async duplicateSession(context?: ChatOperationContext): Promise<void> {
    if (!context?.chatMessages?.length) {
      log.warn('ChatOperations', 'duplicateSession called with no messages');
      return;
    }

    try {
      // This would typically create a new session with the same messages
      console.log('Would duplicate session with', context.chatMessages.length, 'messages');
      log.info('ChatOperations', 'Duplicated session', { 
        originalSessionId: context.chatId,
        messageCount: context.chatMessages.length
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to duplicate session', { error });
      throw error;
    }
  }

  /**
   * Clear chat session
   */
  private async clearSession(context?: ChatOperationContext): Promise<void> {
    if (!context?.chatMessages?.length) {
      log.warn('ChatOperations', 'clearSession called with no messages');
      return;
    }

    const confirmed = confirm(`Are you sure you want to clear all ${context.chatMessages.length} messages in this session?`);
    if (!confirmed) return;

    try {
      await context.clearMessages?.();
      await context.refreshChat?.();
      log.info('ChatOperations', 'Cleared session', { 
        sessionId: context.chatId,
        clearedCount: context.chatMessages.length
      });
    } catch (error) {
      log.error('ChatOperations', 'Failed to clear session', { error });
      throw error;
    }
  }
}

/**
 * Global chat operations instance
 */
export const chatOperations = new ChatOperations();
