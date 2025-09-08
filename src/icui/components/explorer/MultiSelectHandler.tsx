/**
 * ICUI Explorer Multi-Select Handler
 * 
 * Provides multi-select functionality for the Explorer panel using the
 * centralized SelectionModel from Phase 7. Handles Shift/Ctrl selection,
 * keyboard navigation, and selection state management.
 */

import React, { useEffect, useRef, useCallback } from 'react';
import { SelectionModel, SelectionItem, SelectionUtils } from '../../lib/selectionModel';
import { ICUIFileNode } from '../../services';

interface FileSelectionItem extends SelectionItem {
  data: ICUIFileNode;
}

export interface MultiSelectHandlerProps {
  files: ICUIFileNode[];
  selectedIds: string[];
  onSelectionChange: (selectedIds: string[], selectedItems: ICUIFileNode[]) => void;
  onItemClick?: (item: ICUIFileNode, modifiers: { ctrlKey: boolean; shiftKey: boolean; metaKey: boolean }) => void;
  onItemDoubleClick?: (item: ICUIFileNode) => void;
  children: (props: MultiSelectRenderProps) => React.ReactNode;
}

export interface MultiSelectRenderProps {
  isSelected: (itemId: string) => boolean;
  getSelectionCount: () => number;
  handleItemClick: (item: ICUIFileNode, event: React.MouseEvent) => void;
  handleItemDoubleClick: (item: ICUIFileNode, event: React.MouseEvent) => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
  clearSelection: () => void;
  selectAll: () => void;
  selectedItems: ICUIFileNode[];
}

/**
 * Hook for managing Explorer multi-selection
 */
export function useExplorerMultiSelect(
  files: ICUIFileNode[],
  onSelectionChange?: (selectedIds: string[], selectedItems: ICUIFileNode[]) => void
) {
  const selectionModelRef = useRef(new SelectionModel({
    multiSelect: true,
    rangeSelect: true,
  }));

  // Convert files to selection items
  const selectionItems: FileSelectionItem[] = React.useMemo(() => {
    return SelectionUtils.fromArray(files, (file, index) => file.id).map(item => ({
      ...item,
      data: files[item.index],
    })) as FileSelectionItem[];
  }, [files]);

  // Update selection model when files change
  useEffect(() => {
    selectionModelRef.current.setItems(selectionItems);
  }, [selectionItems]);

  // Subscribe to selection changes
  useEffect(() => {
    const unsubscribe = selectionModelRef.current.subscribe((state) => {
      const selectedItems = selectionModelRef.current.getSelectedItems() as FileSelectionItem[];
      const selectedFileData = selectedItems.map(item => item.data);
      onSelectionChange?.(Array.from(state.selectedIds), selectedFileData);
    });

    return unsubscribe;
  }, [onSelectionChange]);

  const handleItemClick = useCallback((
    item: ICUIFileNode,
    modifiers: { ctrlKey: boolean; shiftKey: boolean; metaKey: boolean }
  ) => {
    selectionModelRef.current.select(item.id, modifiers);
  }, []);

  const handleKeyboardNavigation = useCallback((
    direction: 'up' | 'down' | 'home' | 'end',
    modifiers: { shiftKey?: boolean; ctrlKey?: boolean } = {}
  ) => {
    selectionModelRef.current.navigateSelection(direction, modifiers);
  }, []);

  const isSelected = useCallback((itemId: string) => {
    return selectionModelRef.current.isSelected(itemId);
  }, []);

  const getSelectionCount = useCallback(() => {
    return selectionModelRef.current.getSelectionCount();
  }, []);

  const getSelectedItems = useCallback(() => {
    const selectedItems = selectionModelRef.current.getSelectedItems() as FileSelectionItem[];
    return selectedItems.map(item => item.data);
  }, []);

  const clearSelection = useCallback(() => {
    selectionModelRef.current.clearSelection();
  }, []);

  const selectAll = useCallback(() => {
    selectionModelRef.current.selectAll();
  }, []);

  const getSelectedIds = useCallback(() => {
    return selectionModelRef.current.getSelectedIds();
  }, []);

  return {
    handleItemClick,
    handleKeyboardNavigation,
    isSelected,
    getSelectionCount,
    getSelectedItems,
    getSelectedIds,
    clearSelection,
    selectAll,
  };
}

/**
 * Multi-Select Handler Component
 */
export const MultiSelectHandler: React.FC<MultiSelectHandlerProps> = ({
  files,
  selectedIds,
  onSelectionChange,
  onItemClick,
  onItemDoubleClick,
  children,
}) => {
  const {
    handleItemClick: handleMultiSelectClick,
    handleKeyboardNavigation,
    isSelected,
    getSelectionCount,
    getSelectedItems,
    clearSelection,
    selectAll,
  } = useExplorerMultiSelect(files, onSelectionChange);

  // Handle item clicks with multi-select support
  const handleItemClick = useCallback((item: ICUIFileNode, event: React.MouseEvent) => {
    const modifiers = {
      ctrlKey: event.ctrlKey,
      shiftKey: event.shiftKey,
      metaKey: event.metaKey,
    };

    // Let multi-select handler process the selection
    handleMultiSelectClick(item, modifiers);
    
    // Call the external click handler if provided
    onItemClick?.(item, modifiers);
  }, [handleMultiSelectClick, onItemClick]);

  // Handle double-clicks
  const handleItemDoubleClick = useCallback((item: ICUIFileNode, event: React.MouseEvent) => {
    // Double-click should not affect selection for multi-select scenarios
    event.stopPropagation();
    onItemDoubleClick?.(item);
  }, [onItemDoubleClick]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    switch (event.key) {
      case 'ArrowUp':
        event.preventDefault();
        handleKeyboardNavigation('up', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'ArrowDown':
        event.preventDefault();
        handleKeyboardNavigation('down', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'Home':
        event.preventDefault();
        handleKeyboardNavigation('home', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'End':
        event.preventDefault();
        handleKeyboardNavigation('end', { 
          shiftKey: event.shiftKey,
          ctrlKey: event.ctrlKey 
        });
        break;
      case 'a':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault();
          selectAll();
        }
        break;
      case 'Escape':
        event.preventDefault();
        clearSelection();
        break;
      default:
        break;
    }
  }, [handleKeyboardNavigation, selectAll, clearSelection]);

  const selectedItems = getSelectedItems();

  const renderProps: MultiSelectRenderProps = {
    isSelected,
    getSelectionCount,
    handleItemClick,
    handleItemDoubleClick,
    handleKeyDown,
    clearSelection,
    selectAll,
    selectedItems,
  };

  return <>{children(renderProps)}</>;
};

export default MultiSelectHandler;
