/**
 * ICUI Menu Schema and Configuration Model
 * 
 * Declarative schema for context menus usable across panels with clean separation
 * of concerns and extensibility. Supports dynamic predicates and command binding.
 */

export interface MenuItem {
  id: string;
  label: string;
  icon?: string;
  shortcut?: string;
  children?: MenuItem[];
  danger?: boolean;
  separator?: boolean;
  commandId?: string;
  args?: any;
  isVisible?: (context: MenuContext) => boolean;
  isEnabled?: (context: MenuContext) => boolean;
}

export interface MenuContext {
  panelType: string;
  selectedItems?: any[];
  activeItem?: any;
  clipboardContent?: any;
  [key: string]: any;
}

export interface MenuSchema {
  id: string;
  items: MenuItem[];
  context?: MenuContext;
}

/**
 * Standard menu item builders for consistency across panels
 */
export const MenuItems = {
  separator: (id: string): MenuItem => ({
    id,
    label: '',
    separator: true,
  }),

  newFile: (): MenuItem => ({
    id: 'new-file',
    label: 'New File',
    icon: '📄',
    shortcut: 'Ctrl+N',
    commandId: 'file.new',
  }),

  newFolder: (): MenuItem => ({
    id: 'new-folder',
    label: 'New Folder',
    icon: '📁',
    commandId: 'folder.new',
  }),

  rename: (): MenuItem => ({
    id: 'rename',
    label: 'Rename',
    icon: '✏️',
    shortcut: 'F2',
    commandId: 'item.rename',
    isEnabled: (ctx) => ctx.selectedItems?.length === 1,
  }),

  delete: (): MenuItem => ({
    id: 'delete',
    label: 'Delete',
    icon: '🗑️',
    shortcut: 'Delete',
    danger: true,
    commandId: 'item.delete',
    isEnabled: (ctx) => (ctx.selectedItems?.length ?? 0) > 0,
  }),

  duplicate: (): MenuItem => ({
    id: 'duplicate',
    label: 'Duplicate',
    icon: '📋',
    shortcut: 'Ctrl+D',
    commandId: 'item.duplicate',
    isEnabled: (ctx) => (ctx.selectedItems?.length ?? 0) > 0,
  }),

  copy: (): MenuItem => ({
    id: 'copy',
    label: 'Copy',
    icon: '📋',
    shortcut: 'Ctrl+C',
    commandId: 'item.copy',
    isEnabled: (ctx) => (ctx.selectedItems?.length ?? 0) > 0,
  }),

  cut: (): MenuItem => ({
    id: 'cut',
    label: 'Cut',
    icon: '✂️',
    shortcut: 'Ctrl+X',
    commandId: 'item.cut',
    isEnabled: (ctx) => (ctx.selectedItems?.length ?? 0) > 0,
  }),

  paste: (): MenuItem => ({
    id: 'paste',
    label: 'Paste',
    icon: '📋',
    shortcut: 'Ctrl+V',
    commandId: 'item.paste',
    isEnabled: (ctx) => !!ctx.clipboardContent,
  }),

  refresh: (): MenuItem => ({
    id: 'refresh',
    label: 'Refresh',
    icon: '🔄',
    shortcut: 'F5',
    commandId: 'panel.refresh',
  }),
};

/**
 * Standard menu schemas for different panel types
 */
export const MenuSchemas = {
  explorer: (): MenuSchema => ({
    id: 'explorer-context',
    items: [
      MenuItems.newFile(),
      MenuItems.newFolder(),
      MenuItems.separator('sep-1'),
      MenuItems.rename(),
      MenuItems.duplicate(),
      MenuItems.separator('sep-2'),
      MenuItems.copy(),
      MenuItems.cut(),
      MenuItems.paste(),
      MenuItems.separator('sep-3'),
      MenuItems.delete(),
      MenuItems.separator('sep-4'),
      MenuItems.refresh(),
    ],
  }),

  chat: (): MenuSchema => ({
    id: 'chat-context',
    items: [
      MenuItems.rename(),
      MenuItems.duplicate(),
      MenuItems.separator('sep-1'),
      MenuItems.delete(),
    ],
  }),

  terminal: (): MenuSchema => ({
    id: 'terminal-context',
    items: [
      {
        id: 'copy-selection',
        label: 'Copy',
        icon: '📋',
        shortcut: 'Ctrl+C',
        commandId: 'terminal.copy',
      },
      {
        id: 'paste',
        label: 'Paste',
        icon: '📋',
        shortcut: 'Ctrl+V',
        commandId: 'terminal.paste',
      },
      MenuItems.separator('sep-1'),
      {
        id: 'clear',
        label: 'Clear',
        icon: '🧹',
        commandId: 'terminal.clear',
      },
      MenuItems.separator('sep-2'),
      {
        id: 'split-horizontal',
        label: 'Split Horizontally',
        icon: '↔️',
        commandId: 'panel.split',
        args: { direction: 'horizontal' },
      },
      {
        id: 'split-vertical',
        label: 'Split Vertically',
        icon: '↕️',
        commandId: 'panel.split',
        args: { direction: 'vertical' },
      },
    ],
  }),
};

/**
 * Menu schema validation and utilities
 */
export class MenuSchemaUtils {
  static validateMenuItem(item: MenuItem): boolean {
    if (!item.id || !item.label) return false;
    if (item.children) {
      return item.children.every(child => this.validateMenuItem(child));
    }
    return true;
  }

  static validateSchema(schema: MenuSchema): boolean {
    if (!schema.id || !schema.items) return false;
    return schema.items.every(item => this.validateMenuItem(item));
  }

  static filterVisibleItems(items: MenuItem[], context: MenuContext): MenuItem[] {
    return items.filter(item => {
      if (item.isVisible) {
        return item.isVisible(context);
      }
      return true;
    });
  }

  static isItemEnabled(item: MenuItem, context: MenuContext): boolean {
    if (item.isEnabled) {
      return item.isEnabled(context);
    }
    return true;
  }
}
