/**
 * ICUI Explorer Context Menu
 * 
 * Provides context-aware right-click menus for the Explorer panel.
 * Integrates with multi-select and file operations.
 */

import { MenuSchema, MenuItem, MenuContext } from '../../lib/menuSchemas';
import { ICUIFileNode } from '../../services';
import { explorerFileOperations } from './FileOperations';

export interface ExplorerMenuContext extends MenuContext {
  selectedFiles: ICUIFileNode[];
  currentPath: string;
  clickedFile?: ICUIFileNode;
  canPaste: boolean;
  isMultiSelect: boolean;
}

/**
 * Generate context menu schema for Explorer
 */
export function createExplorerContextMenu(context: ExplorerMenuContext): MenuSchema {
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

  return {
    id: 'explorer-context-menu',
    items: items.filter(item => item.isVisible ? item.isVisible(context) : true),
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
