/**
 * ICUI Framework - Layout State Hook
 * React hook for managing layout state in components
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { 
  ICUILayoutHookResult, 
  ICUILayoutState, 
  ICUILayoutPresetType,
  ICUILayoutManagerState
} from '../types/icui-layout-state';
import { ICUILayoutStateManager, createLayoutActions } from '../lib/icui-layout-state';

/**
 * React hook for ICUI layout state management
 */
export function useICUILayoutState(): ICUILayoutHookResult {
  const managerRef = useRef<ICUILayoutStateManager | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layoutState, setLayoutState] = useState<ICUILayoutManagerState | null>(null);

  // Initialize manager
  useEffect(() => {
    try {
      if (!managerRef.current) {
        managerRef.current = new ICUILayoutStateManager();
        setLayoutState(managerRef.current.getState());
      }
      setIsLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize layout state');
      setIsLoading(false);
    }
  }, []);

  // Create actions with manager - using useMemo to prevent recreation
  const actions = useMemo(() => {
    if (!managerRef.current) {
      console.warn('Layout manager not initialized, returning dummy actions');
      return {
        saveLayout: () => console.warn('Cannot save layout: manager not initialized'),
        loadLayout: () => {
          console.warn('Cannot load layout: manager not initialized');
          return null;
        },
        deleteLayout: () => console.warn('Cannot delete layout: manager not initialized'),
        exportLayout: () => {
          console.warn('Cannot export layout: manager not initialized');
          return '{}';
        },
        importLayout: () => {
          console.warn('Cannot import layout: manager not initialized');
          return null;
        },
        applyPreset: () => console.warn('Cannot apply preset: manager not initialized'),
        resetToDefault: () => console.warn('Cannot reset to default: manager not initialized'),
        undo: () => {
          console.warn('Cannot undo: manager not initialized');
          return null;
        },
        redo: () => {
          console.warn('Cannot redo: manager not initialized');
          return null;
        },
      };
    }
    return createLayoutActions(managerRef.current);
  }, [managerRef.current]);

  // Enhanced actions that update local state
  const enhancedActions = useMemo(() => {
    return {
      ...actions,
      saveLayout: (layout: ICUILayoutState) => {
        actions.saveLayout(layout);
        if (managerRef.current) {
          setLayoutState(managerRef.current.getState());
        }
      },
      loadLayout: (layoutId: string) => {
        const result = actions.loadLayout(layoutId);
        if (managerRef.current) {
          setLayoutState(managerRef.current.getState());
        }
        return result;
      },
      applyPreset: (presetType: ICUILayoutPresetType) => {
        actions.applyPreset(presetType);
        if (managerRef.current) {
          setLayoutState(managerRef.current.getState());
        }
      },
      resetToDefault: () => {
        actions.resetToDefault();
        if (managerRef.current) {
          setLayoutState(managerRef.current.getState());
        }
      },
      undo: () => {
        const result = actions.undo();
        if (managerRef.current) {
          setLayoutState(managerRef.current.getState());
        }
        return result;
      },
    };
  }, [actions]);

  return {
    layoutState: layoutState || {
      currentLayout: null,
      presets: [],
      history: [],
      maxHistorySize: 20,
    },
    actions: enhancedActions,
    isLoading,
    error,
  };
}

/**
 * Hook for getting current layout only (read-only)
 */
export function useCurrentLayout(): ICUILayoutState | null {
  const { layoutState } = useICUILayoutState();
  return layoutState?.currentLayout || null;
}

/**
 * Hook for getting available presets
 */
export function useLayoutPresets() {
  const { layoutState } = useICUILayoutState();
  return layoutState?.presets || [];
}
