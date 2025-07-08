/**
 * ICUI Framework - Layout State Management Implementation
 * Handles persistence, presets, and state management for layouts
 */

import { 
  ICUILayoutState, 
  ICUILayoutPreset, 
  ICUILayoutManagerState, 
  ICUILayoutActions,
  ICUILayoutPresetType,
  ICUILayoutPersistence 
} from '../types/icui-layout-state';

const DEFAULT_PERSISTENCE_CONFIG: ICUILayoutPersistence = {
  key: 'icui-layout-state',
  storage: localStorage,
  autoSave: true,
  autoSaveDelay: 1000,
};

/**
 * Layout State Manager Class
 * Handles all layout state operations and persistence
 */
export class ICUILayoutStateManager {
  private state: ICUILayoutManagerState;
  private persistence: ICUILayoutPersistence;
  private autoSaveTimeout: NodeJS.Timeout | null = null;

  constructor(persistenceConfig?: Partial<ICUILayoutPersistence>) {
    this.persistence = { ...DEFAULT_PERSISTENCE_CONFIG, ...persistenceConfig };
    this.state = this.loadFromStorage() || this.getInitialState();
  }

  /**
   * Get initial state with default layout
   */
  private getInitialState(): ICUILayoutManagerState {
    return {
      currentLayout: this.createDefaultLayout(),
      presets: this.getBuiltInPresets(),
      history: [],
      maxHistorySize: 20,
    };
  }

  /**
   * Create default layout configuration
   */
  private createDefaultLayout(): ICUILayoutState {
    const now = new Date().toISOString();
    return {
      id: 'default-layout',
      name: 'Default Layout',
      type: 'default',
      version: '1.0.0',
      createdAt: now,
      modifiedAt: now,
      frameConfig: {
        id: 'main-frame',
        responsive: true,
        borderDetection: true,
        minPanelSize: { width: 200, height: 100 },
        resizeHandleSize: 8,
        snapThreshold: 20,
      },
      splitConfigs: {
        'main-split': {
          id: 'main-split',
          direction: 'horizontal',
          initialSplit: 50,
          minSize: 2,
          collapsible: true,
          resizable: true,
          snapThreshold: 10,
        },
      },
      panelStates: {
        'left-panel': {
          id: 'left-panel',
          type: 'explorer',
          visible: true,
          collapsed: false,
          size: { width: 300, height: 600 },
          position: { x: 0, y: 0 },
          splitParent: 'main-split',
          splitPosition: 25,
        },
        'right-panel': {
          id: 'right-panel',
          type: 'editor',
          visible: true,
          collapsed: false,
          size: { width: 900, height: 600 },
          position: { x: 300, y: 0 },
          splitParent: 'main-split',
          splitPosition: 75,
        },
      },
    };
  }

  /**
   * Get built-in layout presets
   */
  private getBuiltInPresets(): ICUILayoutPreset[] {
    const baseLayout = this.createDefaultLayout();
    
    return [
      {
        id: 'default-preset',
        name: 'Default',
        description: 'Balanced layout with explorer and editor',
        type: 'default',
        config: baseLayout,
      },
      {
        id: 'code-focused-preset',
        name: 'Code Focused',
        description: 'Maximized editor with minimal sidebar',
        type: 'code-focused',
        config: {
          ...baseLayout,
          id: 'code-focused-layout',
          name: 'Code Focused Layout',
          type: 'code-focused',
          splitConfigs: {
            'main-split': {
              ...baseLayout.splitConfigs['main-split'],
              initialSplit: 15, // Smaller left panel
            },
          },
          panelStates: {
            ...baseLayout.panelStates,
            'left-panel': {
              ...baseLayout.panelStates['left-panel'],
              splitPosition: 15,
              size: { width: 180, height: 600 },
            },
            'right-panel': {
              ...baseLayout.panelStates['right-panel'],
              splitPosition: 85,
              size: { width: 1020, height: 600 },
            },
          },
        },
      },
      {
        id: 'terminal-focused-preset',
        name: 'Terminal Focused',
        description: 'Large terminal with code editor',
        type: 'terminal-focused',
        config: {
          ...baseLayout,
          id: 'terminal-focused-layout',
          name: 'Terminal Focused Layout',
          type: 'terminal-focused',
          splitConfigs: {
            'main-split': {
              ...baseLayout.splitConfigs['main-split'],
              direction: 'vertical',
              initialSplit: 40, // Editor on top, terminal below
            },
          },
          panelStates: {
            'top-panel': {
              id: 'top-panel',
              type: 'editor',
              visible: true,
              collapsed: false,
              size: { width: 1200, height: 240 },
              position: { x: 0, y: 0 },
              splitParent: 'main-split',
              splitPosition: 40,
            },
            'bottom-panel': {
              id: 'bottom-panel',
              type: 'terminal',
              visible: true,
              collapsed: false,
              size: { width: 1200, height: 360 },
              position: { x: 0, y: 240 },
              splitParent: 'main-split',
              splitPosition: 60,
            },
          },
        },
      },
    ];
  }

  /**
   * Save layout to storage
   */
  private saveToStorage(): void {
    try {
      const data = JSON.stringify(this.state);
      this.persistence.storage.setItem(this.persistence.key, data);
    } catch (error) {
      console.error('Failed to save layout state:', error);
    }
  }

  /**
   * Load layout from storage
   */
  private loadFromStorage(): ICUILayoutManagerState | null {
    try {
      const data = this.persistence.storage.getItem(this.persistence.key);
      if (data) {
        return JSON.parse(data);
      }
    } catch (error) {
      console.error('Failed to load layout state:', error);
    }
    return null;
  }

  /**
   * Schedule auto-save if enabled
   */
  private scheduleAutoSave(): void {
    if (!this.persistence.autoSave) return;

    if (this.autoSaveTimeout) {
      clearTimeout(this.autoSaveTimeout);
    }

    this.autoSaveTimeout = setTimeout(() => {
      this.saveToStorage();
    }, this.persistence.autoSaveDelay);
  }

  /**
   * Get current state
   */
  public getState(): ICUILayoutManagerState {
    return { ...this.state };
  }

  /**
   * Save layout
   */
  public saveLayout(layout: ICUILayoutState): void {
    // Add to history
    if (this.state.currentLayout) {
      this.state.history.push(this.state.currentLayout);
      
      // Limit history size
      if (this.state.history.length > this.state.maxHistorySize) {
        this.state.history = this.state.history.slice(-this.state.maxHistorySize);
      }
    }

    // Update current layout
    this.state.currentLayout = {
      ...layout,
      modifiedAt: new Date().toISOString(),
    };

    this.scheduleAutoSave();
  }

  /**
   * Load layout by ID
   */
  public loadLayout(layoutId: string): ICUILayoutState | null {
    // Check presets first
    const preset = this.state.presets.find(p => p.id === layoutId);
    if (preset) {
      this.state.currentLayout = preset.config;
      this.scheduleAutoSave();
      return preset.config;
    }

    // Check history
    const historical = this.state.history.find(h => h.id === layoutId);
    if (historical) {
      this.state.currentLayout = historical;
      this.scheduleAutoSave();
      return historical;
    }

    return null;
  }

  /**
   * Apply preset
   */
  public applyPreset(presetType: ICUILayoutPresetType): void {
    const preset = this.state.presets.find(p => p.type === presetType);
    if (preset) {
      this.saveLayout(preset.config);
    }
  }

  /**
   * Export layout as JSON string
   */
  public exportLayout(layout: ICUILayoutState): string {
    try {
      return JSON.stringify(layout, null, 2);
    } catch (error) {
      throw new Error(`Failed to export layout: ${error}`);
    }
  }

  /**
   * Import layout from JSON string
   */
  public importLayout(data: string): ICUILayoutState {
    try {
      const layout = JSON.parse(data) as ICUILayoutState;
      
      // Validate required fields
      if (!layout.id || !layout.name || !layout.frameConfig) {
        throw new Error('Invalid layout data: missing required fields');
      }

      // Generate new ID and timestamps
      const now = new Date().toISOString();
      const importedLayout: ICUILayoutState = {
        ...layout,
        id: `imported-${Date.now()}`,
        createdAt: now,
        modifiedAt: now,
      };

      return importedLayout;
    } catch (error) {
      throw new Error(`Failed to import layout: ${error}`);
    }
  }

  /**
   * Reset to default layout
   */
  public resetToDefault(): void {
    this.applyPreset('default');
  }

  /**
   * Undo last layout change
   */
  public undo(): ICUILayoutState | null {
    if (this.state.history.length === 0) return null;

    const previousLayout = this.state.history.pop()!;
    this.state.currentLayout = previousLayout;
    this.scheduleAutoSave();
    
    return previousLayout;
  }

  /**
   * Get available presets
   */
  public getPresets(): ICUILayoutPreset[] {
    return [...this.state.presets];
  }

  /**
   * Get current layout
   */
  public getCurrentLayout(): ICUILayoutState | null {
    return this.state.currentLayout;
  }
}

/**
 * Create layout actions object
 */
export function createLayoutActions(manager: ICUILayoutStateManager): ICUILayoutActions {
  return {
    saveLayout: (layout) => manager.saveLayout(layout),
    loadLayout: (layoutId) => manager.loadLayout(layoutId),
    deleteLayout: () => {
      throw new Error('Delete layout not yet implemented');
    },
    exportLayout: (layout) => manager.exportLayout(layout),
    importLayout: (data) => manager.importLayout(data),
    applyPreset: (presetType) => manager.applyPreset(presetType),
    resetToDefault: () => manager.resetToDefault(),
    undo: () => manager.undo(),
    redo: () => {
      throw new Error('Redo not yet implemented');
    },
  };
}
