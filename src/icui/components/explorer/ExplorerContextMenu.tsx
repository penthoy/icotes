/**
 * ICUI Explorer Context Menu
 * 
 * Provides context-aware right-click menus for the Explorer panel.
 * Integrates with multi-select and file operations.
 * Supports extensibility via custom commands and menu groups.
 */

import { MenuSchema, MenuItem, MenuContext } from '../../lib/menuSchemas';
import { ICUIFileNode } from '../../services';
import { explorerFileOperations } from './FileOperations';
import { globalCommandRegistry } from '../../lib/commandRegistry';

export interface ExplorerMenuContext extends MenuContext {
  selectedFiles: ICUIFileNode[];
  currentPath: string;
  clickedFile?: ICUIFileNode;
  canPaste: boolean;
  isMultiSelect: boolean;
}

export interface CustomMenuGroup {
  id: string;
  label?: string;
  separator?: boolean;
  position?: 'before' | 'after';
  anchor?: string; // ID of menu item to position relative to
  items: MenuItem[];
  priority?: number; // Lower numbers appear first
}

export interface ExplorerMenuExtensions {
  customGroups?: CustomMenuGroup[];
  customCommands?: string[]; // Command IDs from global registry
  hiddenItems?: string[]; // Menu item IDs to hide
}

/**
 * Generate context menu schema for Explorer with extensibility support
 */
export function createExplorerContextMenu(
  context: ExplorerMenuContext, 
  extensions?: ExplorerMenuExtensions
): MenuSchema {
  const { selectedFiles, clickedFile, canPaste, isMultiSelect } = context;
  const hasSelection = selectedFiles.length > 0;
  const singleSelection = selectedFiles.length === 1;
  const multipleSelection = selectedFiles.length > 1;
  const isFile = singleSelection && selectedFiles[0].type === 'file';
  const isFolder = singleSelection && selectedFiles[0].type === 'folder';

  const items: MenuItem[] = [];

  // New File/Folder (always available when right-clicking in empty space or folder)
  if (!hasSelection || (singleSelection && isFolder)) {
    items.push(
      {
        id: 'newFile',
        label: 'New File',
        icon: '📄',
        shortcut: 'Ctrl+N',
        commandId: 'explorer.newFile',
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'newFolder',
        label: 'New Folder',
        icon: '📁',
        shortcut: 'Ctrl+Shift+N',
        commandId: 'explorer.newFolder',
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'separator1',
        label: '',
        separator: true,
        isVisible: () => true,
      }
    );
  }

  // File/Folder operations (when items are selected)
  if (hasSelection) {
    // Copy
    items.push({
      id: 'copy',
      label: multipleSelection ? `Copy ${selectedFiles.length} items` : 'Copy',
      icon: '📋',
      shortcut: 'Ctrl+C',
      commandId: 'explorer.copy',
      isVisible: () => true,
      isEnabled: () => true,
    });

    // Cut
    items.push({
      id: 'cut',
      label: multipleSelection ? `Cut ${selectedFiles.length} items` : 'Cut',
      icon: '✂️',
      shortcut: 'Ctrl+X',
      commandId: 'explorer.cut',
      isVisible: () => true,
      isEnabled: () => true,
    });

    // Duplicate
    items.push({
      id: 'duplicate',
      label: multipleSelection ? `Duplicate ${selectedFiles.length} items` : 'Duplicate',
      icon: '📋',
      shortcut: 'Ctrl+D',
      commandId: 'explorer.duplicate',
      isVisible: () => true,
      isEnabled: () => true,
    });

    items.push({
      id: 'separator2',
      label: '',
      separator: true,
      isVisible: () => true,
    });

    // Rename (only for single selection)
    items.push({
      id: 'rename',
      label: 'Rename',
      icon: '✏️',
      shortcut: 'F2',
      commandId: 'explorer.rename',
      isVisible: () => singleSelection,
      isEnabled: () => singleSelection,
    });

    // Delete
    items.push({
      id: 'delete',
      label: multipleSelection ? `Delete ${selectedFiles.length} items` : 'Delete',
      icon: '🗑️',
      shortcut: 'Delete',
      commandId: 'explorer.delete',
      danger: true,
      isVisible: () => true,
      isEnabled: () => true,
    });

    items.push({
      id: 'separator3',
      label: '',
      separator: true,
      isVisible: () => true,
    });

    // Download actions (Phase 5)
    items.push({
      id: 'download',
      label: multipleSelection ? `Download ${selectedFiles.length} items` : 'Download',
      icon: '⬇️',
      commandId: 'explorer.download',
      isVisible: () => true,
      isEnabled: () => true,
    });

    // Reveal in OS (only for single selection)
    items.push({
      id: 'revealInOS',
      label: 'Reveal in File Manager',
      icon: '🔍',
      commandId: 'explorer.revealInOS',
      isVisible: () => singleSelection,
      isEnabled: () => singleSelection,
    });
  }

  // Paste (available when clipboard has content)
  if (canPaste) {
    const clipboardStatus = explorerFileOperations.getClipboardStatus();
    const label = clipboardStatus 
      ? `Paste ${clipboardStatus.count} item${clipboardStatus.count > 1 ? 's' : ''} (${clipboardStatus.operation})`
      : 'Paste';

    items.push({
      id: 'paste',
      label,
      icon: '📄',
      shortcut: 'Ctrl+V',
      commandId: 'explorer.paste',
      isVisible: () => true,
      isEnabled: () => true,
    });
  }

  // Add separator before general actions if we have any items
  if (items.length > 0) {
    items.push({
      id: 'separator4',
      label: '',
      separator: true,
      isVisible: () => true,
    });
  }

  // Refresh (always available)
  items.push({
    id: 'refresh',
    label: 'Refresh',
    icon: '🔄',
    shortcut: 'F5',
    commandId: 'explorer.refresh',
    isVisible: () => true,
    isEnabled: () => true,
  });

  // Selection actions (when multi-select is active)
  if (isMultiSelect) {
    items.push(
      {
        id: 'separator5',
        label: '',
        separator: true,
        isVisible: () => true,
      },
      {
        id: 'selectAll',
        label: 'Select All',
        icon: '☑️',
        shortcut: 'Ctrl+A',
        // This would be handled by the multi-select handler, not command registry
        isVisible: () => true,
        isEnabled: () => true,
      },
      {
        id: 'clearSelection',
        label: 'Clear Selection',
        icon: '◻️',
        shortcut: 'Esc',
        // This would be handled by the multi-select handler, not command registry
        isVisible: () => hasSelection,
        isEnabled: () => hasSelection,
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
        if (command && command.category === 'explorer') {
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
        id: 'explorer-context-menu',
        items: items.filter(item => 
          !hiddenSet.has(item.id) && 
          (item.isVisible ? item.isVisible(context) : true)
        ),
      };
    }
  }

  return {
    id: 'explorer-context-menu',
    items: items.filter(item => item.isVisible ? item.isVisible(context) : true),
  };
}

/**
 * Register a custom Explorer command
 */
export function registerExplorerCommand(
  id: string,
  label: string,
  handler: (context: ExplorerMenuContext) => void | Promise<void>,
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
    category: 'explorer',
    description: options.description,
    icon: options.icon,
    shortcut: options.shortcut,
    enabled: options.enabled !== false,
    visible: options.visible !== false,
  });
}

/**
 * Create a custom menu group for Explorer
 */
export function createCustomMenuGroup(
  id: string,
  items: MenuItem[],
  options: {
    label?: string;
    separator?: boolean;
    position?: 'before' | 'after';
    anchor?: string;
    priority?: number;
  } = {}
): CustomMenuGroup {
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

/**
 * Handle context menu item clicks for Explorer
 */
export function handleExplorerContextMenuClick(
  item: MenuItem,
  context: ExplorerMenuContext,
  multiSelectActions: {
    selectAll: () => void;
    clearSelection: () => void;
  }
): void {
  // Handle multi-select specific actions
  switch (item.id) {
    case 'selectAll':
      multiSelectActions.selectAll();
      return;
    case 'clearSelection':
      multiSelectActions.clearSelection();
      return;
    default:
      // All other actions are handled by the command registry
      // The command execution is handled by the ContextMenu component
      break;
  }
}
