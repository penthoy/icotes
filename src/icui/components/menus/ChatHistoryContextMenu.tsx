/**
 * ICUI Chat History Context Menu
 * 
 * Provides context-aware right-click menus for Chat History sessions.
 * Supports single and multi-select operations for session management.
 */

import { MenuSchema, MenuItem, MenuContext } from '../../lib/menuSchemas';
import { globalCommandRegistry } from '../../lib/commandRegistry';

export interface ChatHistorySession {
  id: string;
  name: string;
  updated: number;
  messageCount?: number;
}

export interface ChatHistoryMenuContext extends MenuContext {
  selectedSessions: ChatHistorySession[];
  totalSessions: number;
  canRename: boolean;
  canDelete: boolean;
  canDuplicate: boolean;
  canExport: boolean;
}

export interface CustomChatHistoryMenuGroup {
  id: string;
  label?: string;
  separator?: boolean;
  position?: 'before' | 'after';
  anchor?: string;
  items: MenuItem[];
  priority?: number;
}

export interface ChatHistoryMenuExtensions {
  customGroups?: CustomChatHistoryMenuGroup[];
  customCommands?: string[];
  hiddenItems?: string[];
}

/**
 * Generate context menu schema for Chat History sessions
 */
export function createChatHistoryContextMenu(
  context: ChatHistoryMenuContext,
  extensions?: ChatHistoryMenuExtensions
): MenuSchema {
  const { selectedSessions, canRename, canDelete, canDuplicate, canExport } = context;
  const hasSelection = selectedSessions.length > 0;
  const isSingleSelection = selectedSessions.length === 1;
  const isMultiSelection = selectedSessions.length > 1;

  const items: MenuItem[] = [];

  // Single session actions
  if (isSingleSelection) {
    items.push(
      {
        id: 'chatHistory.open',
        label: 'Open Session',
        icon: '📂',
      },
      { id: 'separator-1', label: '', separator: true }
    );

    if (canRename) {
      items.push({
        id: 'chatHistory.rename',
        label: 'Rename',
        icon: '✏️',
        shortcut: 'F2',
      });
    }

    if (canDuplicate) {
      items.push({
        id: 'chatHistory.duplicate',
        label: 'Duplicate Session',
        icon: '📋',
      });
    }
  }

  // Multi-selection actions
  if (hasSelection) {
    if (canExport) {
      items.push({
        id: 'chatHistory.export',
        label: isMultiSelection ? `Export ${selectedSessions.length} Sessions` : 'Export Session',
        icon: '💾',
      });
    }

    items.push({ id: 'separator-2', label: '', separator: true });

    if (canDelete) {
      items.push({
        id: 'chatHistory.delete',
        label: isMultiSelection ? `Delete ${selectedSessions.length} Sessions` : 'Delete Session',
        icon: '🗑️',
        danger: true,
      });
    }
  }

  // Session management actions (when no selection or for general operations)
  if (!hasSelection || isSingleSelection) {
    items.push({ id: 'separator-3', label: '', separator: true });
    
    items.push({
      id: 'chatHistory.newSession',
      label: 'New Chat Session',
      icon: '➕',
      shortcut: 'Ctrl+N',
    });

    items.push({
      id: 'chatHistory.refresh',
      label: 'Refresh Sessions',
      icon: '🔄',
      shortcut: 'F5',
    });
  }

  // Bulk operations (when multiple sessions available)
  if (context.totalSessions > 1) {
    items.push({ id: 'separator-4', label: '', separator: true });

    items.push({
      id: 'chatHistory.selectAll',
      label: 'Select All Sessions',
      icon: '☑️',
      shortcut: 'Ctrl+A',
    });

    items.push({
      id: 'chatHistory.clearAll',
      label: 'Clear All Sessions',
      icon: '🧹',
      danger: true,
    });
  }

  // Add custom commands from extensions
  if (extensions?.customCommands && extensions.customCommands.length > 0) {
    items.push({ id: 'separator-custom', label: '', separator: true });
    
    extensions.customCommands.forEach(commandId => {
      const command = globalCommandRegistry.getCommand(commandId);
      if (command) {
        items.push({
          id: commandId,
          label: command.label || commandId,
          icon: command.icon,
        });
      }
    });
  }

  // Add custom groups
  if (extensions?.customGroups && extensions.customGroups.length > 0) {
    extensions.customGroups.forEach(group => {
      if (group.separator) {
        items.push({ id: `separator-${group.id}`, label: '', separator: true });
      }
      items.push(...group.items);
    });
  }

  // Filter out hidden items
  const visibleItems = extensions?.hiddenItems 
    ? items.filter(item => !extensions.hiddenItems!.includes(item.id))
    : items;

  return {
    id: 'chatHistory-context-menu',
    items: visibleItems,
  };
}

/**
 * Handle context menu item clicks for Chat History
 */
export function handleChatHistoryContextMenuClick(
  item: MenuItem,
  context: ChatHistoryMenuContext
): void {
  // Execute via command registry for extensibility
  globalCommandRegistry.execute(item.id, context).catch(error => {
    console.warn('ChatHistory context menu command failed:', error);
  });
}

/**
 * Register a custom command for Chat History
 */
export function registerChatHistoryCommand(
  id: string,
  label: string,
  handler: (context: ChatHistoryMenuContext) => void | Promise<void>,
  options: {
    icon?: string;
    description?: string;
  } = {}
): void {
  globalCommandRegistry.register({
    id,
    label,
    description: options.description,
    icon: options.icon,
    handler: async (context) => {
      await handler(context as ChatHistoryMenuContext);
    },
  });
}

/**
 * Create a custom menu group for Chat History
 */
export function createCustomChatHistoryMenuGroup(
  id: string,
  items: MenuItem[],
  options: {
    label?: string;
    separator?: boolean;
    position?: 'before' | 'after';
    anchor?: string;
    priority?: number;
  } = {}
): CustomChatHistoryMenuGroup {
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
