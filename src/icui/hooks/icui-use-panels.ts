/**
 * ICUI Framework - Panel Management Hook
 * React hook for managing panel instances and state
 */

import { useState, useCallback, useRef, useMemo } from 'react';
import { 
  ICUIPanelInstance, 
  ICUIPanelConfig, 
  ICUIPanelState, 
  ICUIPanelPosition,
  ICUIPanelActions,
  ICUIPanelHookResult,
  ICUIPanelManagerState,
  ICUIPanelType 
} from '../types/icui-panel';

/**
 * Generate unique panel ID
 */
function generatePanelId(): string {
  return `icui-panel-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Create default panel configuration
 */
function createDefaultPanelConfig(type: ICUIPanelType): ICUIPanelConfig {
  const now = new Date().toISOString();
  
  return {
    id: generatePanelId(),
    type,
    title: `${type.charAt(0).toUpperCase() + type.slice(1)} Panel`,
    closable: true,
    resizable: true,
    minimizable: true,
    maximizable: true,
    draggable: true,
    contentType: 'scrollable',
    defaultState: 'normal',
    minSize: {
      width: 200,
      height: 100,
    },
    maxSize: {
      width: 1200,
      height: 800,
    },
  };
}

/**
 * Create default panel position
 */
function createDefaultPosition(): ICUIPanelPosition {
  return {
    x: 100 + Math.random() * 200,
    y: 100 + Math.random() * 200,
    width: 400,
    height: 300,
    zIndex: 1000,
  };
}

/**
 * Create panel instance from config
 */
function createPanelInstance(config: ICUIPanelConfig): ICUIPanelInstance {
  const now = new Date().toISOString();
  
  return {
    id: config.id,
    config,
    state: config.defaultState,
    position: createDefaultPosition(),
    isActive: false,
    createdAt: now,
    modifiedAt: now,
  };
}

/**
 * React hook for panel management
 */
export function useICUIPanels(): ICUIPanelHookResult {
  const [panelManagerState, setPanelManagerState] = useState<ICUIPanelManagerState>({
    panels: {},
    activePanel: null,
    panelOrder: [],
    defaultConfigs: {
      terminal: {},
      editor: {},
      explorer: {},
      output: {},
      properties: {},
      timeline: {},
      inspector: {},
      custom: {},
    },
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nextZIndex = useRef(1000);

  // Get panels array
  const panels = useMemo(() => {
    return panelManagerState.panelOrder.map(id => panelManagerState.panels[id]).filter(Boolean);
  }, [panelManagerState.panels, panelManagerState.panelOrder]);

  // Get active panel
  const activePanel = useMemo(() => {
    return panelManagerState.activePanel ? panelManagerState.panels[panelManagerState.activePanel] : null;
  }, [panelManagerState.activePanel, panelManagerState.panels]);

  // Create panel action
  const createPanel = useCallback((config: ICUIPanelConfig): ICUIPanelInstance => {
    const instance = createPanelInstance(config);
    instance.position.zIndex = nextZIndex.current++;
    
    setPanelManagerState(prev => ({
      ...prev,
      panels: {
        ...prev.panels,
        [instance.id]: instance,
      },
      panelOrder: [...prev.panelOrder, instance.id],
      activePanel: instance.id,
    }));
    
    return instance;
  }, []);

  // Update panel action
  const updatePanel = useCallback((id: string, updates: Partial<ICUIPanelInstance>) => {
    setPanelManagerState(prev => {
      const panel = prev.panels[id];
      if (!panel) return prev;
      
      const updatedPanel = {
        ...panel,
        ...updates,
        modifiedAt: new Date().toISOString(),
      };
      
      return {
        ...prev,
        panels: {
          ...prev.panels,
          [id]: updatedPanel,
        },
      };
    });
  }, []);

  // Remove panel action
  const removePanel = useCallback((id: string) => {
    setPanelManagerState(prev => {
      const newPanels = { ...prev.panels };
      delete newPanels[id];
      
      const newOrder = prev.panelOrder.filter(panelId => panelId !== id);
      const newActivePanel = prev.activePanel === id 
        ? (newOrder.length > 0 ? newOrder[newOrder.length - 1] : null)
        : prev.activePanel;
      
      return {
        ...prev,
        panels: newPanels,
        panelOrder: newOrder,
        activePanel: newActivePanel,
      };
    });
  }, []);

  // Set panel state action
  const setPanelStateById = useCallback((id: string, state: ICUIPanelState) => {
    updatePanel(id, { state });
  }, [updatePanel]);

  // Set panel position action
  const setPanelPosition = useCallback((id: string, position: Partial<ICUIPanelPosition>) => {
    updatePanel(id, { 
      position: {
        ...panelManagerState.panels[id]?.position,
        ...position,
      }
    });
  }, [updatePanel, panelManagerState.panels]);

  // Set active panel action
  const setActivePanel = useCallback((id: string) => {
    const panel = panelManagerState.panels[id];
    if (!panel) return;
    
    // Update z-index for active panel
    const newZIndex = nextZIndex.current++;
    
    setPanelManagerState(prev => ({
      ...prev,
      activePanel: id,
      panels: {
        ...prev.panels,
        [id]: {
          ...panel,
          position: {
            ...panel.position,
            zIndex: newZIndex,
          },
          isActive: true,
        },
        // Deactivate other panels
        ...Object.fromEntries(
          Object.entries(prev.panels)
            .filter(([panelId]) => panelId !== id)
            .map(([panelId, p]) => [panelId, { ...p, isActive: false }])
        ),
      },
    }));
  }, [panelManagerState.panels]);

  // Clone panel action
  const clonePanel = useCallback((id: string): ICUIPanelInstance => {
    const panel = panelManagerState.panels[id];
    if (!panel) {
      throw new Error(`Panel with id "${id}" not found`);
    }
    
    const clonedConfig = {
      ...panel.config,
      id: generatePanelId(),
      title: `${panel.config.title} (Copy)`,
    };
    
    const clonedInstance = createPanelInstance(clonedConfig);
    clonedInstance.position = {
      ...panel.position,
      x: panel.position.x + 20,
      y: panel.position.y + 20,
      zIndex: nextZIndex.current++,
    };
    
    setPanelManagerState(prev => ({
      ...prev,
      panels: {
        ...prev.panels,
        [clonedInstance.id]: clonedInstance,
      },
      panelOrder: [...prev.panelOrder, clonedInstance.id],
      activePanel: clonedInstance.id,
    }));
    
    return clonedInstance;
  }, [panelManagerState.panels]);

  // Panel actions object
  const actions: ICUIPanelActions = useMemo(() => ({
    create: createPanel,
    update: updatePanel,
    remove: removePanel,
    setState: setPanelStateById,
    setPosition: setPanelPosition,
    setActive: setActivePanel,
    clone: clonePanel,
  }), [createPanel, updatePanel, removePanel, setPanelStateById, setPanelPosition, setActivePanel, clonePanel]);

  return {
    panels,
    activePanel,
    actions,
    isLoading,
    error,
  };
}

/**
 * Create a panel with default configuration
 */
export function createPanel(type: ICUIPanelType, overrides?: Partial<ICUIPanelConfig>): ICUIPanelConfig {
  const defaultConfig = createDefaultPanelConfig(type);
  
  return {
    ...defaultConfig,
    ...overrides,
    id: overrides?.id || generatePanelId(),
  };
}

/**
 * Panel utility functions
 */
export const PanelUtils = {
  generateId: generatePanelId,
  createDefaultConfig: createDefaultPanelConfig,
  createDefaultPosition,
  createInstance: createPanelInstance,
};
