/**
 * ICUI Context-Aware Command Integration
 * 
 * Enhanced command registry integration that wires ContextMenu to actionRegistry 
 * for command execution with per-panel context injection and error handling.
 */

import { globalCommandRegistry, Command, CommandContext } from './commandRegistry';
import { MenuItem, MenuContext } from './menuSchemas';
import { useNotifications } from '../services/notificationService';

/**
 * Panel-specific context types
 */
export interface PanelContext extends CommandContext {
  panelType: 'terminal' | 'editor' | 'explorer' | 'chat' | 'chatHistory';
  panelId: string;
  
  // Explorer-specific context
  selectedFiles?: string[];
  selectedFolders?: string[];
  currentDirectory?: string;
  clipboardFiles?: { action: 'copy' | 'cut'; files: string[] };
  
  // Chat-specific context  
  selectedMessages?: string[];
  currentSession?: string;
  
  // Terminal-specific context
  terminalInstance?: any;
  selectedText?: string;
  
  // Editor-specific context
  openFiles?: string[];
  activeFile?: string;
  selection?: any;
  
  // Common context
  workspace?: string;
  [key: string]: any;
}

/**
 * Context menu command executor with panel-aware context injection
 */
export class ContextMenuCommandExecutor {
  private notificationService: any;

  constructor() {
    // Will be injected via hook in React components
    this.notificationService = null;
  }

  /**
   * Execute a menu item command with panel context
   */
  async executeMenuItem(
    item: MenuItem, 
    panelContext: PanelContext,
    notificationService?: any
  ): Promise<void> {
    if (!item.commandId) {
      console.warn('Menu item has no command ID:', item);
      return;
    }

    // Use injected notification service
    const notifications = notificationService || this.notificationService;

    try {
      // Get command from registry
      const command = globalCommandRegistry.getCommand(item.commandId);
      if (!command) {
        const error = `Command not found: ${item.commandId}`;
        console.error(error);
        notifications?.showError(error);
        return;
      }

      // Check if command is enabled
      if (!command.enabled) {
        const warning = `Command is disabled: ${command.label}`;
        console.warn(warning);
        notifications?.showWarning(warning);
        return;
      }

      // Build enhanced context with panel-specific data
      const enhancedContext: PanelContext = {
        ...panelContext,
        commandId: item.commandId,
        menuItem: item,
        args: item.args,
      };

      // Execute command with context
      await globalCommandRegistry.execute(item.commandId, enhancedContext);
      
      // Show success notification for important actions
      if (item.danger || item.label.toLowerCase().includes('delete')) {
        notifications?.showSuccess(`${command.label} completed successfully`);
      }

    } catch (error) {
      const errorMessage = `Failed to execute ${item.label}: ${error.message || error}`;
      console.error(errorMessage, error);
      notifications?.showError(errorMessage);
    }
  }

  /**
   * Batch execute multiple commands (for multi-selection scenarios)
   */
  async executeBatchMenuItems(
    items: MenuItem[],
    panelContext: PanelContext,
    notificationService?: any
  ): Promise<void> {
    const notifications = notificationService || this.notificationService;
    
    if (items.length === 0) return;
    
    // Show progress for batch operations
    if (items.length > 1) {
      notifications?.showInfo(`Executing ${items.length} operations...`);
    }

    const results = await Promise.allSettled(
      items.map(item => this.executeMenuItem(item, panelContext, notificationService))
    );

    // Report batch results
    const successful = results.filter(r => r.status === 'fulfilled').length;
    const failed = results.filter(r => r.status === 'rejected').length;

    if (failed > 0) {
      notifications?.showError(`${successful}/${items.length} operations completed. ${failed} failed.`);
    } else if (items.length > 1) {
      notifications?.showSuccess(`All ${successful} operations completed successfully.`);
    }
  }

  /**
   * Check if a menu item can be executed in the current context
   */
  canExecuteMenuItem(item: MenuItem, panelContext: PanelContext): boolean {
    if (!item.commandId) return false;
    
    const command = globalCommandRegistry.getCommand(item.commandId);
    if (!command || !command.enabled) return false;

    // Check item-specific enabled predicate
    if (item.isEnabled && !item.isEnabled(this.buildMenuContext(panelContext))) {
      return false;
    }

    return true;
  }

  /**
   * Convert panel context to menu context for predicates
   */
  private buildMenuContext(panelContext: PanelContext): MenuContext {
    return {
      panelType: panelContext.panelType,
      selectedItems: this.getSelectedItems(panelContext),
      activeItem: this.getActiveItem(panelContext),
      clipboardContent: this.getClipboardContent(panelContext),
      ...panelContext,
    };
  }

  private getSelectedItems(context: PanelContext): any[] {
    switch (context.panelType) {
      case 'explorer':
        return [...(context.selectedFiles || []), ...(context.selectedFolders || [])];
      case 'chat':
      case 'chatHistory':
        return context.selectedMessages || [];
      default:
        return [];
    }
  }

  private getActiveItem(context: PanelContext): any {
    switch (context.panelType) {
      case 'explorer':
        return context.currentDirectory;
      case 'editor':
        return context.activeFile;
      case 'chat':
      case 'chatHistory':
        return context.currentSession;
      case 'terminal':
        return context.terminalInstance;
      default:
        return null;
    }
  }

  private getClipboardContent(context: PanelContext): any {
    switch (context.panelType) {
      case 'explorer':
        return context.clipboardFiles;
      case 'terminal':
        return context.selectedText;
      default:
        return null;
    }
  }
}

/**
 * Global command executor instance
 */
export const globalContextMenuExecutor = new ContextMenuCommandExecutor();

/**
 * React hook for context menu command execution
 */
export function useContextMenuCommands(panelContext: PanelContext) {
  const { success, error, warning, info } = useNotifications();

  const executeMenuItem = async (item: MenuItem) => {
    await globalContextMenuExecutor.executeMenuItem(
      item, 
      panelContext, 
      { showSuccess: success, showError: error, showWarning: warning, showInfo: info }
    );
  };

  const executeBatchMenuItems = async (items: MenuItem[]) => {
    await globalContextMenuExecutor.executeBatchMenuItems(
      items, 
      panelContext, 
      { showSuccess: success, showError: error, showWarning: warning, showInfo: info }
    );
  };

  const canExecuteMenuItem = (item: MenuItem): boolean => {
    return globalContextMenuExecutor.canExecuteMenuItem(item, panelContext);
  };

  return {
    executeMenuItem,
    executeBatchMenuItems,
    canExecuteMenuItem,
  };
}

/**
 * Standard panel commands that can be registered by any panel
 */
export const StandardPanelCommands = {
  // File operations
  FILE_NEW: 'file.new',
  FILE_OPEN: 'file.open', 
  FILE_SAVE: 'file.save',
  FILE_SAVE_AS: 'file.saveAs',
  FILE_RENAME: 'file.rename',
  FILE_DELETE: 'file.delete',
  FILE_DUPLICATE: 'file.duplicate',
  
  // Folder operations
  FOLDER_NEW: 'folder.new',
  FOLDER_RENAME: 'folder.rename', 
  FOLDER_DELETE: 'folder.delete',
  
  // Clipboard operations
  EDIT_CUT: 'edit.cut',
  EDIT_COPY: 'edit.copy',
  EDIT_PASTE: 'edit.paste',
  
  // Selection operations
  SELECT_ALL: 'select.all',
  SELECT_NONE: 'select.none',
  SELECT_INVERT: 'select.invert',
  
  // Panel operations
  PANEL_CLOSE: 'panel.close',
  PANEL_DUPLICATE: 'panel.duplicate',
  PANEL_SPLIT_HORIZONTAL: 'panel.splitHorizontal',
  PANEL_SPLIT_VERTICAL: 'panel.splitVertical',
  
  // Terminal operations  
  TERMINAL_CLEAR: 'terminal.clear',
  TERMINAL_COPY_SELECTION: 'terminal.copySelection',
  TERMINAL_PASTE: 'terminal.paste',
  
  // Chat operations
  CHAT_NEW_SESSION: 'chat.newSession',
  CHAT_RENAME_SESSION: 'chat.renameSession',
  CHAT_DELETE_SESSION: 'chat.deleteSession',
  CHAT_EXPORT_SESSION: 'chat.exportSession',
  
  // View operations
  VIEW_REFRESH: 'view.refresh',
  VIEW_TOGGLE_HIDDEN: 'view.toggleHidden',
  
} as const;

export default ContextMenuCommandExecutor;
