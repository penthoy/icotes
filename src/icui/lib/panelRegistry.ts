/**
 * ICUI Panel Registry
 * 
 * Central registry for available panel types and their default context menus.
 * Stores panel metadata (icons, descriptions) and capabilities.
 */

import { MenuSchema, MenuItem, MenuItems } from './menuSchemas';
import { StandardPanelCommands } from './contextMenuIntegration';

/**
 * Panel type definitions
 */
export type PanelType = 'terminal' | 'editor' | 'explorer' | 'chat' | 'chatHistory';

/**
 * Panel capabilities that determine available actions
 */
export interface PanelCapabilities {
  supportsDuplicate: boolean;
  supportsRename: boolean;
  supportsClose: boolean;
  supportsMaximize: boolean;
  supportsMinimize: boolean;
  supportsSplitHorizontal: boolean;
  supportsSplitVertical: boolean;
  supportsFileOperations: boolean;
  supportsMultiSelect: boolean;
  supportsClipboard: boolean;
  supportsSearch: boolean;
  supportsSort: boolean;
  supportsFilter: boolean;
  customCapabilities?: string[];
}

/**
 * Panel metadata including display information and behavior
 */
export interface PanelMetadata {
  id: string;
  type: PanelType;
  displayName: string;
  description: string;
  icon: string;
  category: 'core' | 'development' | 'communication' | 'utility' | 'custom';
  capabilities: PanelCapabilities;
  defaultContextMenu: MenuSchema;
  defaultSize?: { width?: number | string; height?: number | string };
  minSize?: { width?: number; height?: number };
  maxSize?: { width?: number; height?: number };
  defaultPosition?: 'left' | 'right' | 'top' | 'bottom' | 'center';
  tags?: string[];
}

/**
 * Panel Registry class manages available panel types
 */
export class PanelRegistry {
  private panels: Map<PanelType, PanelMetadata> = new Map();
  private listeners: Set<(event: PanelRegistryEvent) => void> = new Set();

  /**
   * Register a panel type with its metadata
   */
  register(metadata: PanelMetadata): void {
    this.panels.set(metadata.type, { ...metadata });
    this.emit({ type: 'panel-registered', panelType: metadata.type, metadata });
  }

  /**
   * Unregister a panel type
   */
  unregister(panelType: PanelType): boolean {
    const metadata = this.panels.get(panelType);
    if (!metadata) return false;

    this.panels.delete(panelType);
    this.emit({ type: 'panel-unregistered', panelType, metadata });
    return true;
  }

  /**
   * Get panel metadata by type
   */
  getPanel(panelType: PanelType): PanelMetadata | undefined {
    return this.panels.get(panelType);
  }

  /**
   * Get all registered panels
   */
  getAllPanels(): PanelMetadata[] {
    return Array.from(this.panels.values());
  }

  /**
   * Get panels by category
   */
  getPanelsByCategory(category: PanelMetadata['category']): PanelMetadata[] {
    return this.getAllPanels().filter(panel => panel.category === category);
  }

  /**
   * Search panels by name, description, or tags
   */
  searchPanels(query: string): PanelMetadata[] {
    const lowercaseQuery = query.toLowerCase();
    return this.getAllPanels().filter(panel => 
      panel.displayName.toLowerCase().includes(lowercaseQuery) ||
      panel.description.toLowerCase().includes(lowercaseQuery) ||
      panel.tags?.some(tag => tag.toLowerCase().includes(lowercaseQuery))
    );
  }

  /**
   * Check if a panel type is registered
   */
  isRegistered(panelType: PanelType): boolean {
    return this.panels.has(panelType);
  }

  /**
   * Get default context menu for a panel type
   */
  getDefaultContextMenu(panelType: PanelType): MenuSchema | undefined {
    const panel = this.getPanel(panelType);
    return panel?.defaultContextMenu;
  }

  /**
   * Update panel metadata
   */
  updatePanel(panelType: PanelType, updates: Partial<PanelMetadata>): boolean {
    const existing = this.panels.get(panelType);
    if (!existing) return false;

    const updated = { ...existing, ...updates };
    this.panels.set(panelType, updated);
    this.emit({ type: 'panel-updated', panelType, metadata: updated });
    return true;
  }

  /**
   * Subscribe to registry events
   */
  subscribe(listener: (event: PanelRegistryEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(event: PanelRegistryEvent): void {
    this.listeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in panel registry event listener:', error);
      }
    });
  }
}

/**
 * Panel registry event types
 */
export type PanelRegistryEvent = 
  | { type: 'panel-registered'; panelType: PanelType; metadata: PanelMetadata }
  | { type: 'panel-unregistered'; panelType: PanelType; metadata: PanelMetadata }
  | { type: 'panel-updated'; panelType: PanelType; metadata: PanelMetadata };

/**
 * Default panel capabilities helper
 */
export class PanelCapabilitiesBuilder {
  private capabilities: PanelCapabilities;

  constructor() {
    this.capabilities = {
      supportsDuplicate: true,
      supportsRename: false,
      supportsClose: true,
      supportsMaximize: true,
      supportsMinimize: true,
      supportsSplitHorizontal: true,
      supportsSplitVertical: true,
      supportsFileOperations: false,
      supportsMultiSelect: false,
      supportsClipboard: false,
      supportsSearch: false,
      supportsSort: false,
      supportsFilter: false,
    };
  }

  duplicate(enabled: boolean): this {
    this.capabilities.supportsDuplicate = enabled;
    return this;
  }

  rename(enabled: boolean): this {
    this.capabilities.supportsRename = enabled;
    return this;
  }

  close(enabled: boolean): this {
    this.capabilities.supportsClose = enabled;
    return this;
  }

  maximize(enabled: boolean): this {
    this.capabilities.supportsMaximize = enabled;
    return this;
  }

  minimize(enabled: boolean): this {
    this.capabilities.supportsMinimize = enabled;
    return this;
  }

  split(horizontal: boolean, vertical: boolean): this {
    this.capabilities.supportsSplitHorizontal = horizontal;
    this.capabilities.supportsSplitVertical = vertical;
    return this;
  }

  fileOperations(enabled: boolean): this {
    this.capabilities.supportsFileOperations = enabled;
    return this;
  }

  multiSelect(enabled: boolean): this {
    this.capabilities.supportsMultiSelect = enabled;
    return this;
  }

  clipboard(enabled: boolean): this {
    this.capabilities.supportsClipboard = enabled;
    return this;
  }

  search(enabled: boolean): this {
    this.capabilities.supportsSearch = enabled;
    return this;
  }

  sort(enabled: boolean): this {
    this.capabilities.supportsSort = enabled;
    return this;
  }

  filter(enabled: boolean): this {
    this.capabilities.supportsFilter = enabled;
    return this;
  }

  custom(capabilities: string[]): this {
    this.capabilities.customCapabilities = capabilities;
    return this;
  }

  build(): PanelCapabilities {
    return { ...this.capabilities };
  }
}

/**
 * Default context menu builders for each panel type
 */
export class DefaultContextMenus {
  static terminal(): MenuSchema {
    return {
      id: 'terminal-context-menu',
      items: [
        {
          id: 'terminal-copy',
          label: 'Copy Selection',
          icon: '📋',
          shortcut: 'Ctrl+C',
          commandId: StandardPanelCommands.TERMINAL_COPY_SELECTION,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        {
          id: 'terminal-paste',
          label: 'Paste',
          icon: '📥',
          shortcut: 'Ctrl+V',
          commandId: StandardPanelCommands.TERMINAL_PASTE,
        },
        MenuItems.separator('terminal-sep1'),
        {
          id: 'terminal-clear',
          label: 'Clear Terminal',
          icon: '🗑️',
          commandId: StandardPanelCommands.TERMINAL_CLEAR,
        },
        MenuItems.separator('terminal-sep2'),
        {
          id: 'panel-split-h',
          label: 'Split Horizontally',
          icon: '⬌',
          commandId: StandardPanelCommands.PANEL_SPLIT_HORIZONTAL,
        },
        {
          id: 'panel-split-v',
          label: 'Split Vertically',
          icon: '⬍',
          commandId: StandardPanelCommands.PANEL_SPLIT_VERTICAL,
        },
        {
          id: 'panel-duplicate',
          label: 'Duplicate Panel',
          icon: '⧉',
          commandId: StandardPanelCommands.PANEL_DUPLICATE,
        },
        MenuItems.separator('terminal-sep3'),
        {
          id: 'panel-close',
          label: 'Close Panel',
          icon: '✕',
          commandId: StandardPanelCommands.PANEL_CLOSE,
          danger: true,
        },
      ],
    };
  }

  static editor(): MenuSchema {
    return {
      id: 'editor-context-menu',
      items: [
        MenuItems.newFile(),
        {
          id: 'file-save',
          label: 'Save',
          icon: '💾',
          shortcut: 'Ctrl+S',
          commandId: StandardPanelCommands.FILE_SAVE,
        },
        {
          id: 'file-save-as',
          label: 'Save As...',
          icon: '💾',
          shortcut: 'Ctrl+Shift+S',
          commandId: StandardPanelCommands.FILE_SAVE_AS,
        },
        MenuItems.separator('editor-sep1'),
        {
          id: 'edit-cut',
          label: 'Cut',
          icon: '✂️',
          shortcut: 'Ctrl+X',
          commandId: StandardPanelCommands.EDIT_CUT,
        },
        {
          id: 'edit-copy',
          label: 'Copy',
          icon: '📋',
          shortcut: 'Ctrl+C',
          commandId: StandardPanelCommands.EDIT_COPY,
        },
        {
          id: 'edit-paste',
          label: 'Paste',
          icon: '📥',
          shortcut: 'Ctrl+V',
          commandId: StandardPanelCommands.EDIT_PASTE,
        },
        MenuItems.separator('editor-sep2'),
        {
          id: 'panel-close',
          label: 'Close Panel',
          icon: '✕',
          commandId: StandardPanelCommands.PANEL_CLOSE,
          danger: true,
        },
      ],
    };
  }

  static explorer(): MenuSchema {
    return {
      id: 'explorer-context-menu',
      items: [
        MenuItems.newFile(),
        MenuItems.newFolder(),
        MenuItems.separator('explorer-sep1'),
        {
          id: 'file-rename',
          label: 'Rename',
          icon: '✏️',
          shortcut: 'F2',
          commandId: StandardPanelCommands.FILE_RENAME,
          isEnabled: (ctx) => ctx.selectedItems?.length === 1,
        },
        {
          id: 'file-duplicate',
          label: 'Duplicate',
          icon: '⧉',
          commandId: StandardPanelCommands.FILE_DUPLICATE,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        {
          id: 'file-delete',
          label: 'Delete',
          icon: '🗑️',
          shortcut: 'Delete',
          commandId: StandardPanelCommands.FILE_DELETE,
          danger: true,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        MenuItems.separator('explorer-sep2'),
        {
          id: 'edit-cut',
          label: 'Cut',
          icon: '✂️',
          shortcut: 'Ctrl+X',
          commandId: StandardPanelCommands.EDIT_CUT,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        {
          id: 'edit-copy',
          label: 'Copy',
          icon: '📋',
          shortcut: 'Ctrl+C',
          commandId: StandardPanelCommands.EDIT_COPY,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        {
          id: 'edit-paste',
          label: 'Paste',
          icon: '📥',
          shortcut: 'Ctrl+V',
          commandId: StandardPanelCommands.EDIT_PASTE,
          isEnabled: (ctx) => !!ctx.clipboardContent,
        },
        MenuItems.separator('explorer-sep3'),
        {
          id: 'select-all',
          label: 'Select All',
          icon: '☑️',
          shortcut: 'Ctrl+A',
          commandId: StandardPanelCommands.SELECT_ALL,
        },
        {
          id: 'view-refresh',
          label: 'Refresh',
          icon: '🔄',
          shortcut: 'F5',
          commandId: StandardPanelCommands.VIEW_REFRESH,
        },
      ],
    };
  }

  static chat(): MenuSchema {
    return {
      id: 'chat-context-menu',
      items: [
        {
          id: 'chat-new-session',
          label: 'New Session',
          icon: '💬',
          commandId: StandardPanelCommands.CHAT_NEW_SESSION,
        },
        {
          id: 'chat-rename-session',
          label: 'Rename Session',
          icon: '✏️',
          commandId: StandardPanelCommands.CHAT_RENAME_SESSION,
          isEnabled: (ctx) => !!ctx.activeItem,
        },
        {
          id: 'chat-export-session',
          label: 'Export Session',
          icon: '📤',
          commandId: StandardPanelCommands.CHAT_EXPORT_SESSION,
          isEnabled: (ctx) => !!ctx.activeItem,
        },
        MenuItems.separator('chat-sep1'),
        {
          id: 'chat-delete-session',
          label: 'Delete Session',
          icon: '🗑️',
          commandId: StandardPanelCommands.CHAT_DELETE_SESSION,
          danger: true,
          isEnabled: (ctx) => !!ctx.activeItem,
        },
        MenuItems.separator('chat-sep2'),
        {
          id: 'panel-duplicate',
          label: 'Duplicate Panel',
          icon: '⧉',
          commandId: StandardPanelCommands.PANEL_DUPLICATE,
        },
        {
          id: 'panel-close',
          label: 'Close Panel',
          icon: '✕',
          commandId: StandardPanelCommands.PANEL_CLOSE,
          danger: true,
        },
      ],
    };
  }

  static chatHistory(): MenuSchema {
    return {
      id: 'chat-history-context-menu',
      items: [
        {
          id: 'edit-copy',
          label: 'Copy Message',
          icon: '📋',
          shortcut: 'Ctrl+C',
          commandId: StandardPanelCommands.EDIT_COPY,
          isEnabled: (ctx) => !!ctx.selectedItems?.length,
        },
        MenuItems.separator('chat-history-sep1'),
        {
          id: 'chat-export-session',
          label: 'Export Session',
          icon: '📤',
          commandId: StandardPanelCommands.CHAT_EXPORT_SESSION,
        },
        {
          id: 'view-refresh',
          label: 'Refresh',
          icon: '🔄',
          commandId: StandardPanelCommands.VIEW_REFRESH,
        },
      ],
    };
  }
}

/**
 * Pre-built panel metadata for core panel types
 */
export class CorePanelMetadata {
  static terminal(): PanelMetadata {
    return {
      id: 'core-terminal',
      type: 'terminal',
      displayName: 'Terminal',
      description: 'Interactive command line interface',
      icon: '💻',
      category: 'development',
      capabilities: new PanelCapabilitiesBuilder()
        .clipboard(true)
        .build(),
      defaultContextMenu: DefaultContextMenus.terminal(),
      defaultPosition: 'bottom',
      tags: ['terminal', 'command', 'shell', 'development'],
    };
  }

  static editor(): PanelMetadata {
    return {
      id: 'core-editor',
      type: 'editor',
      displayName: 'Code Editor',
      description: 'Source code editor with syntax highlighting',
      icon: '📝',
      category: 'development',
      capabilities: new PanelCapabilitiesBuilder()
        .fileOperations(true)
        .clipboard(true)
        .search(true)
        .build(),
      defaultContextMenu: DefaultContextMenus.editor(),
      defaultPosition: 'center',
      tags: ['editor', 'code', 'text', 'development'],
    };
  }

  static explorer(): PanelMetadata {
    return {
      id: 'core-explorer',
      type: 'explorer',
      displayName: 'File Explorer',
      description: 'File and folder navigation',
      icon: '📁',
      category: 'core',
      capabilities: new PanelCapabilitiesBuilder()
        .fileOperations(true)
        .multiSelect(true)
        .clipboard(true)
        .search(true)
        .sort(true)
        .filter(true)
        .build(),
      defaultContextMenu: DefaultContextMenus.explorer(),
      defaultPosition: 'left',
      tags: ['files', 'folders', 'navigation', 'filesystem'],
    };
  }

  static chat(): PanelMetadata {
    return {
      id: 'core-chat',
      type: 'chat',
      displayName: 'AI Chat',
      description: 'Interactive AI assistant chat interface',
      icon: '🤖',
      category: 'communication',
      capabilities: new PanelCapabilitiesBuilder()
        .clipboard(true)
        .search(true)
        .build(),
      defaultContextMenu: DefaultContextMenus.chat(),
      defaultPosition: 'right',
      tags: ['ai', 'chat', 'assistant', 'communication'],
    };
  }

  static chatHistory(): PanelMetadata {
    return {
      id: 'core-chat-history',
      type: 'chatHistory',
      displayName: 'Chat History',
      description: 'Chat session history and management',
      icon: '📜',
      category: 'communication',
      capabilities: new PanelCapabilitiesBuilder()
        .clipboard(true)
        .search(true)
        .sort(true)
        .filter(true)
        .build(),
      defaultContextMenu: DefaultContextMenus.chatHistory(),
      defaultPosition: 'right',
      tags: ['history', 'sessions', 'chat', 'communication'],
    };
  }
}

/**
 * Global panel registry instance
 */
export const globalPanelRegistry = new PanelRegistry();

// Register core panels
globalPanelRegistry.register(CorePanelMetadata.terminal());
globalPanelRegistry.register(CorePanelMetadata.editor());
globalPanelRegistry.register(CorePanelMetadata.explorer());
globalPanelRegistry.register(CorePanelMetadata.chat());
globalPanelRegistry.register(CorePanelMetadata.chatHistory());

export default PanelRegistry;
