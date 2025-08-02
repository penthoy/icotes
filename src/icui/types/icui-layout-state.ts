/**
 * ICUI Framework - Layout State Management Types
 * Types for persisting and managing layout configurations
 */

import { ICUIFrameConfig } from './icui-layout';
import { ICUISplitConfig } from './icui-split';

export type ICUILayoutPresetType = 'default' | 'code-focused' | 'terminal-focused' | 'split-view' | 'custom';

export interface ICUILayoutState {
  id: string;
  name: string;
  type: ICUILayoutPresetType;
  version: string;
  createdAt: string;
  modifiedAt: string;
  frameConfig: ICUIFrameConfig;
  splitConfigs: Record<string, ICUISplitConfig>;
  panelStates: Record<string, ICUIPanelState>;
}

export interface ICUIPanelState {
  id: string;
  type: string;
  visible: boolean;
  collapsed: boolean;
  size: {
    width: number;
    height: number;
  };
  position: {
    x: number;
    y: number;
  };
  splitParent?: string;
  splitPosition?: number;
}

export interface ICUILayoutPreset {
  id: string;
  name: string;
  description: string;
  type: ICUILayoutPresetType;
  thumbnail?: string;
  config: ICUILayoutState;
}

export interface ICUILayoutManagerState {
  currentLayout: ICUILayoutState | null;
  presets: ICUILayoutPreset[];
  history: ICUILayoutState[];
  maxHistorySize: number;
}

export interface ICUILayoutActions {
  saveLayout: (layout: ICUILayoutState) => void;
  loadLayout: (layoutId: string) => ICUILayoutState | null;
  deleteLayout: (layoutId: string) => void;
  exportLayout: (layout: ICUILayoutState) => string;
  importLayout: (data: string) => ICUILayoutState;
  applyPreset: (presetType: ICUILayoutPresetType) => void;
  resetToDefault: () => void;
  undo: () => ICUILayoutState | null;
  redo: () => ICUILayoutState | null;
}

export interface ICUILayoutPersistence {
  key: string;
  storage: Storage;
  autoSave: boolean;
  autoSaveDelay: number;
}

export interface ICUILayoutHookResult {
  layoutState: ICUILayoutManagerState;
  actions: ICUILayoutActions;
  isLoading: boolean;
  error: string | null;
}
