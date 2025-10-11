import { useCallback } from 'react';
import { ICUIFileNode } from '../../services';
import { useContextMenu } from '../ui/ContextMenu';
import { explorerFileOperations } from './FileOperations';
import { ExplorerMenuContext, ExplorerMenuExtensions, createExplorerContextMenu, handleExplorerContextMenuClick } from './ExplorerContextMenu';
import { globalCommandRegistry } from '../../lib/commandRegistry';

export function useExplorerContextMenu(params: {
  currentPath: string;
  getSelectedItems: () => ICUIFileNode[];
  isSelected: (id: string) => boolean;
  handleMultiSelectClick: (item: ICUIFileNode, opts: { ctrlKey: boolean; shiftKey: boolean; metaKey: boolean }) => void;
  extensions?: ExplorerMenuExtensions;
  selectAll: () => void;
  clearSelection: () => void;
  setError: (msg: string) => void;
  startRename: (file: ICUIFileNode) => void;
}) {
  const { currentPath, getSelectedItems, isSelected, handleMultiSelectClick, extensions, selectAll, clearSelection, setError, startRename } = params;

  const { contextMenu, showContextMenu, hideContextMenu } = useContextMenu();

  const handleContextMenu = useCallback((event: React.MouseEvent, clickedFile?: ICUIFileNode) => {
    event.preventDefault();
    event.stopPropagation();

    if (clickedFile && !isSelected(clickedFile.id)) {
      handleMultiSelectClick(clickedFile, { ctrlKey: false, shiftKey: false, metaKey: false });
    }

    const currentSelection = clickedFile && !isSelected(clickedFile.id)
      ? [clickedFile]
      : getSelectedItems();

    const menuContext: ExplorerMenuContext = {
      panelType: 'explorer',
      selectedFiles: currentSelection,
      currentPath,
      clickedFile,
      canPaste: explorerFileOperations.canPaste(),
      isMultiSelect: true,
      selectedItems: currentSelection,
      targetDirectoryPath: clickedFile && clickedFile.type === 'folder' ? clickedFile.path : currentPath,
    } as any;

    const schema = createExplorerContextMenu(menuContext, extensions);
    showContextMenu(event, schema, menuContext);
  }, [isSelected, handleMultiSelectClick, getSelectedItems, currentPath, showContextMenu, extensions]);

  const handleMenuItemClick = useCallback((item: any) => {
    const selectedItems = getSelectedItems();
    const clickedFolder = selectedItems.length === 1 && selectedItems[0].type === 'folder' ? selectedItems[0] : undefined;
    const menuContext: ExplorerMenuContext = {
      panelType: 'explorer',
      selectedFiles: selectedItems,
      currentPath,
      canPaste: explorerFileOperations.canPaste(),
      isMultiSelect: true,
      selectedItems,
      targetDirectoryPath: clickedFolder ? clickedFolder.path : currentPath,
    } as any;

    handleExplorerContextMenuClick(item, menuContext, {
      selectAll,
      clearSelection,
    });

    if (item.commandId === 'explorer.rename' && selectedItems.length === 1) {
      startRename(selectedItems[0]);
      return;
    }

    if (item.commandId) {
      const enrichedContext = { ...menuContext, args: item.args } as any;
      globalCommandRegistry.execute(item.commandId, enrichedContext).catch(error => {
        console.error('[useExplorerContextMenu] Failed to execute command:', error);
        setError(error.message);
      });
    }
  }, [getSelectedItems, currentPath, selectAll, clearSelection, startRename, setError]);

  return { contextMenu, showContextMenu, hideContextMenu, handleContextMenu, handleMenuItemClick } as const;
}
