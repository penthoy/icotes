/**
 * ICUI Chat Context Menu
 * 
 * Provides context-aware right-click menus for Chat history items.
 * Supports single item actions and extensibility.
 */

import { MenuSchema, MenuItem, MenuContext } from '../../lib/menuSchemas';
import { ChatMessage } from '../../types/chatTypes';
import { globalCommandRegistry } from '../../lib/commandRegistry';

export interface ChatMenuContext extends MenuContext {
  selectedMessage?: ChatMessage;
  chatMessages: ChatMessage[];
  chatId?: string;
  canRename: boolean;
  canDelete: boolean;
  canExport: boolean;
}

export interface CustomChatMenuGroup {
  id: string;
  label?: string;
  separator?: boolean;
  position?: 'before' | 'after';
  anchor?: string; // ID of menu item to position relative to
  items: MenuItem[];
  priority?: number; // Lower numbers appear first
}

export interface ChatMenuExtensions {
  customGroups?: CustomChatMenuGroup[];
  customCommands?: string[]; // Command IDs from global registry
  hiddenItems?: string[]; // Menu item IDs to hide
}

/**
 * Generate context menu schema for Chat with extensibility support
 */
export function createChatContextMenu(
  context: ChatMenuContext, 
  extensions?: ChatMenuExtensions
): MenuSchema {
  const { selectedMessage, chatMessages, canRename, canDelete, canExport } = context;
  const hasMessage = !!selectedMessage;
  const isUserMessage = hasMessage && selectedMessage.sender === 'user';
  const isAgentMessage = hasMessage && selectedMessage.sender === 'ai';

  const items: MenuItem[] = [];

  // Message-specific actions (when a message is selected)
  if (hasMessage) {
    // Copy message content
    items.push({
      id: 'copyMessage',
      label: 'Copy Message',
      icon: '📋',
      shortcut: 'Ctrl+C',
      commandId: 'chat.copyMessage',
      isVisible: () => true,
      isEnabled: () => true,
    });

    // Quote/Reply to message (for agent messages)
    if (isAgentMessage) {
      items.push({
        id: 'quoteMessage',
        label: 'Quote & Reply',
        icon: '💬',
        commandId: 'chat.quoteMessage',
        isVisible: () => true,
        isEnabled: () => true,
      });
    }

    // Regenerate response (for agent messages)
    if (isAgentMessage) {
      items.push({
        id: 'regenerateResponse',
        label: 'Regenerate Response',
        icon: '🔄',
        shortcut: 'Ctrl+R',
        commandId: 'chat.regenerateResponse',
        isVisible: () => true,
        isEnabled: () => true,
      });
    }

    items.push({
      id: 'separator1',
      label: '',
      separator: true,
      isVisible: () => true,
    });

    // Edit message (for user messages)
    if (isUserMessage) {
      items.push({
        id: 'editMessage',
        label: 'Edit Message',
        icon: '✏️',
        shortcut: 'F2',
        commandId: 'chat.editMessage',
        isVisible: () => true,
        isEnabled: () => true,
      });
    }

    // Delete message
    items.push({
      id: 'deleteMessage',
      label: 'Delete Message',
      icon: '🗑️',
      shortcut: 'Delete',
      commandId: 'chat.deleteMessage',
      danger: true,
      isVisible: () => canDelete,
      isEnabled: () => canDelete,
    });

    items.push({
      id: 'separator2',
      label: '',
      separator: true,
      isVisible: () => true,
    });
  }

  // Session-level actions
  items.push(
    {
      id: 'newSession',
      label: 'New Chat Session',
      icon: '➕',
      shortcut: 'Ctrl+N',
      commandId: 'chat.newSession',
      isVisible: () => true,
      isEnabled: () => true,
    },
    {
      id: 'renameSession',
      label: 'Rename Session',
      icon: '✏️',
      shortcut: 'F2',
      commandId: 'chat.renameSession',
      isVisible: () => canRename,
      isEnabled: () => canRename,
    }
  );

  // Export actions
  if (canExport && chatMessages.length > 0) {
    items.push(
      {
        id: 'separator3',
        label: '',
        separator: true,
        isVisible: () => true,
      },
      {
        id: 'exportSession',
        label: 'Export Session',
        icon: '📤',
        commandId: 'chat.exportSession',
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'duplicateSession',
        label: 'Duplicate Session',
        icon: '📄',
        commandId: 'chat.duplicateSession',
        isVisible: () => true,
        isEnabled: () => true,
      }
    );
  }

  // Clear/Reset actions
  if (chatMessages.length > 0) {
    items.push(
      {
        id: 'separator4',
        label: '',
        separator: true,
        isVisible: () => true,
      },
      {
        id: 'clearSession',
        label: 'Clear Session',
        icon: '🧹',
        shortcut: 'Ctrl+Shift+K',
        commandId: 'chat.clearSession',
        danger: true,
        isVisible: () => true,
        isEnabled: () => true,
      }
    );
  }

  // Apply extensions if provided
  if (extensions) {
    // Add custom commands from global registry
    if (extensions.customCommands) {
      const customItems: MenuItem[] = [];
      
      extensions.customCommands.forEach(commandId => {
        const command = globalCommandRegistry.getCommand(commandId);
        if (command && command.category === 'chat') {
          customItems.push({
            id: commandId,
            label: command.label,
            icon: command.icon,
            shortcut: command.shortcut,
            commandId: command.id,
            isVisible: () => command.visible !== false,
            isEnabled: () => command.enabled !== false,
          });
        }
      });

      if (customItems.length > 0) {
        items.push(
          {
            id: 'customSeparator',
            label: '',
            separator: true,
            isVisible: () => true,
          },
          ...customItems
        );
      }
    }

    // Insert custom menu groups at specified positions
    if (extensions.customGroups) {
      extensions.customGroups
        .sort((a, b) => (a.priority || 100) - (b.priority || 100))
        .forEach(group => {
          const groupItems: MenuItem[] = [];

          // Add group separator/label if specified
          if (group.separator || group.label) {
            groupItems.push({
              id: `${group.id}-separator`,
              label: group.label || '',
              separator: true,
              isVisible: () => true,
            });
          }

          // Add group items
          groupItems.push(...group.items);

          // Insert at specified position
          if (group.position && group.anchor) {
            const anchorIndex = items.findIndex(item => item.id === group.anchor);
            if (anchorIndex !== -1) {
              const insertIndex = group.position === 'before' ? anchorIndex : anchorIndex + 1;
              items.splice(insertIndex, 0, ...groupItems);
            } else {
              // Fallback: append to end
              items.push(...groupItems);
            }
          } else {
            // No specific position: append to end
            items.push(...groupItems);
          }
        });
    }

    // Filter out hidden items
    if (extensions.hiddenItems) {
      const hiddenSet = new Set(extensions.hiddenItems);
      return {
        id: 'chat-context-menu',
        items: items.filter(item => 
          !hiddenSet.has(item.id) && 
          (item.isVisible ? item.isVisible(context) : true)
        ),
      };
    }
  }

  return {
    id: 'chat-context-menu',
    items: items.filter(item => item.isVisible ? item.isVisible(context) : true),
  };
}

/**
 * Handle context menu item clicks for Chat
 */
export function handleChatContextMenuClick(
  item: MenuItem,
  context: ChatMenuContext
): void {
  // All actions are handled by the command registry
  // The command execution is handled by the ContextMenu component
}

/**
 * Register a custom Chat command
 */
export function registerChatCommand(
  id: string,
  label: string,
  handler: (context: ChatMenuContext) => void | Promise<void>,
  options: {
    icon?: string;
    shortcut?: string;
    description?: string;
    enabled?: boolean;
    visible?: boolean;
  } = {}
): void {
  globalCommandRegistry.register({
    id,
    label,
    handler,
    category: 'chat',
    description: options.description,
    icon: options.icon,
    shortcut: options.shortcut,
    enabled: options.enabled !== false,
    visible: options.visible !== false,
  });
}

/**
 * Create a custom menu group for Chat
 */
export function createCustomChatMenuGroup(
  id: string,
  items: MenuItem[],
  options: {
    label?: string;
    separator?: boolean;
    position?: 'before' | 'after';
    anchor?: string;
    priority?: number;
  } = {}
): CustomChatMenuGroup {
  return {
    id,
    items,
    label: options.label,
    separator: options.separator,
    position: options.position,
    anchor: options.anchor,
    priority: options.priority,
  };
}
