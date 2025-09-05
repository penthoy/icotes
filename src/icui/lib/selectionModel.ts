/**
 * ICUI Selection Model Foundation
 * 
 * Selection model to support Shift/Ctrl multi-select across files and folders.
 * Pure, testable logic with no DOM coupling. Provides foundation for Explorer
 * and other panels that need multi-selection capabilities.
 */

export interface SelectionItem {
  id: string;
  index: number;
  data?: any;
}

export interface SelectionState {
  selectedIds: Set<string>;
  anchorId: string | null;
  lastSelectedId: string | null;
  items: SelectionItem[];
}

export interface SelectionOptions {
  multiSelect?: boolean;
  rangeSelect?: boolean;
}

export class SelectionModel {
  private state: SelectionState;
  private options: SelectionOptions;
  private listeners: Set<(state: SelectionState) => void>;

  constructor(options: SelectionOptions = {}) {
    this.state = {
      selectedIds: new Set(),
      anchorId: null,
      lastSelectedId: null,
      items: [],
    };
    this.options = {
      multiSelect: true,
      rangeSelect: true,
      ...options,
    };
    this.listeners = new Set();
  }

  /**
   * Set the available items for selection
   */
  setItems(items: SelectionItem[]): void {
    this.state.items = [...items];
    
    // Remove selected items that no longer exist
    const validIds = new Set(items.map(item => item.id));
    this.state.selectedIds = new Set(
      Array.from(this.state.selectedIds).filter(id => validIds.has(id))
    );
    
    // Clear anchor and last selected if they no longer exist
    if (this.state.anchorId && !validIds.has(this.state.anchorId)) {
      this.state.anchorId = null;
    }
    if (this.state.lastSelectedId && !validIds.has(this.state.lastSelectedId)) {
      this.state.lastSelectedId = null;
    }
    
    this.notifyListeners();
  }

  /**
   * Handle click selection with modifier keys
   */
  select(
    itemId: string,
    modifiers: {
      ctrlKey?: boolean;
      shiftKey?: boolean;
      metaKey?: boolean;
    } = {}
  ): void {
    const item = this.state.items.find(i => i.id === itemId);
    if (!item) return;

    const { ctrlKey = false, shiftKey = false, metaKey = false } = modifiers;
    const isMultiSelect = (ctrlKey || metaKey) && this.options.multiSelect;
    const isRangeSelect = shiftKey && this.options.rangeSelect;

    if (isRangeSelect && this.state.anchorId) {
      this.selectRange(this.state.anchorId, itemId);
    } else if (isMultiSelect) {
      this.toggleSelection(itemId);
    } else {
      this.setSingleSelection(itemId);
    }

    this.state.lastSelectedId = itemId;
    if (!isRangeSelect) {
      this.state.anchorId = itemId;
    }

    this.notifyListeners();
  }

  /**
   * Select a range of items between two IDs
   */
  private selectRange(fromId: string, toId: string): void {
    const fromIndex = this.state.items.findIndex(item => item.id === fromId);
    const toIndex = this.state.items.findIndex(item => item.id === toId);
    
    if (fromIndex === -1 || toIndex === -1) return;

    const startIndex = Math.min(fromIndex, toIndex);
    const endIndex = Math.max(fromIndex, toIndex);

    // Clear current selection
    this.state.selectedIds.clear();

    // Select range
    for (let i = startIndex; i <= endIndex; i++) {
      this.state.selectedIds.add(this.state.items[i].id);
    }
  }

  /**
   * Toggle selection of a single item
   */
  private toggleSelection(itemId: string): void {
    if (this.state.selectedIds.has(itemId)) {
      this.state.selectedIds.delete(itemId);
    } else {
      this.state.selectedIds.add(itemId);
    }
  }

  /**
   * Set single item selection (clear others)
   */
  private setSingleSelection(itemId: string): void {
    this.state.selectedIds.clear();
    this.state.selectedIds.add(itemId);
  }

  /**
   * Select all items
   */
  selectAll(): void {
    this.state.selectedIds.clear();
    this.state.items.forEach(item => {
      this.state.selectedIds.add(item.id);
    });
    this.notifyListeners();
  }

  /**
   * Clear all selections
   */
  clearSelection(): void {
    this.state.selectedIds.clear();
    this.state.anchorId = null;
    this.state.lastSelectedId = null;
    this.notifyListeners();
  }

  /**
   * Get current selection state
   */
  getState(): Readonly<SelectionState> {
    return {
      selectedIds: new Set(this.state.selectedIds),
      anchorId: this.state.anchorId,
      lastSelectedId: this.state.lastSelectedId,
      items: [...this.state.items],
    };
  }

  /**
   * Get selected items data
   */
  getSelectedItems(): SelectionItem[] {
    return this.state.items.filter(item => 
      this.state.selectedIds.has(item.id)
    );
  }

  /**
   * Get selected IDs as array
   */
  getSelectedIds(): string[] {
    return Array.from(this.state.selectedIds);
  }

  /**
   * Check if an item is selected
   */
  isSelected(itemId: string): boolean {
    return this.state.selectedIds.has(itemId);
  }

  /**
   * Get selection count
   */
  getSelectionCount(): number {
    return this.state.selectedIds.size;
  }

  /**
   * Subscribe to selection changes
   */
  subscribe(listener: (state: SelectionState) => void): () => void {
    this.listeners.add(listener);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify all listeners of state changes
   */
  private notifyListeners(): void {
    const state = this.getState();
    this.listeners.forEach(listener => listener(state));
  }

  /**
   * Handle keyboard navigation
   */
  navigateSelection(direction: 'up' | 'down' | 'home' | 'end', modifiers: {
    shiftKey?: boolean;
    ctrlKey?: boolean;
  } = {}): void {
    if (this.state.items.length === 0) return;

    let targetIndex = 0;
    const currentIndex = this.state.lastSelectedId 
      ? this.state.items.findIndex(item => item.id === this.state.lastSelectedId)
      : -1;

    switch (direction) {
      case 'up':
        targetIndex = Math.max(0, currentIndex - 1);
        break;
      case 'down':
        targetIndex = Math.min(this.state.items.length - 1, currentIndex + 1);
        break;
      case 'home':
        targetIndex = 0;
        break;
      case 'end':
        targetIndex = this.state.items.length - 1;
        break;
    }

    const targetItem = this.state.items[targetIndex];
    if (targetItem) {
      this.select(targetItem.id, modifiers);
    }
  }
}

/**
 * Selection utilities for common operations
 */
export class SelectionUtils {
  static createSelectionItem(id: string, index: number, data?: any): SelectionItem {
    return { id, index, data };
  }

  static fromArray<T>(
    items: T[], 
    getId: (item: T, index: number) => string
  ): SelectionItem[] {
    return items.map((item, index) => ({
      id: getId(item, index),
      index,
      data: item,
    }));
  }

  static getContiguousRanges(selectedIndices: number[]): { start: number; end: number }[] {
    if (selectedIndices.length === 0) return [];

    const sorted = [...selectedIndices].sort((a, b) => a - b);
    const ranges: { start: number; end: number }[] = [];
    let start = sorted[0];
    let end = sorted[0];

    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i] === end + 1) {
        end = sorted[i];
      } else {
        ranges.push({ start, end });
        start = sorted[i];
        end = sorted[i];
      }
    }

    ranges.push({ start, end });
    return ranges;
  }
}
