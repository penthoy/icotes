/**
 * ICUI Framework - Panel System Types
 * Types for the generic panel base class and panel system
 */

export type ICUIPanelType = 
  | 'terminal' 
  | 'editor' 
  | 'explorer' 
  | 'output' 
  | 'properties' 
  | 'timeline' 
  | 'inspector'
  | 'custom';

export type ICUIPanelState = 'normal' | 'minimized' | 'maximized' | 'closed';

export type ICUIPanelContentType = 'scrollable' | 'fixed' | 'flexible';

export interface ICUIPanelConfig {
  id: string;
  type: ICUIPanelType;
  title: string;
  closable: boolean;
  resizable: boolean;
  minimizable: boolean;
  maximizable: boolean;
  draggable: boolean;
  contentType: ICUIPanelContentType;
  defaultState: ICUIPanelState;
  minSize?: {
    width: number;
    height: number;
  };
  maxSize?: {
    width: number;
    height: number;
  };
  icon?: string;
  contextMenuItems?: ICUIPanelContextMenuItem[];
}

export interface ICUIPanelContextMenuItem {
  id: string;
  label: string;
  icon?: string;
  action: () => void;
  separator?: boolean;
  disabled?: boolean;
}

export interface ICUIPanelPosition {
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
}

export interface ICUIPanelInstance {
  id: string;
  config: ICUIPanelConfig;
  state: ICUIPanelState;
  position: ICUIPanelPosition;
  isActive: boolean;
  createdAt: string;
  modifiedAt: string;
}

export interface ICUIPanelHeaderProps {
  panel: ICUIPanelInstance;
  onStateChange: (state: ICUIPanelState) => void;
  onTitleChange?: (title: string) => void;
  onTypeChange?: (type: ICUIPanelType) => void;
  onClose?: () => void;
  onDragStart?: (event: React.MouseEvent) => void;
  editable?: boolean;
  showControls?: boolean;
}

export interface ICUIPanelContentProps {
  panel: ICUIPanelInstance;
  children: React.ReactNode;
  className?: string;
  padding?: boolean;
  scrollable?: boolean;
}

export interface ICUIBasePanelProps {
  panel: ICUIPanelInstance;
  children: React.ReactNode;
  className?: string;
  onStateChange?: (state: ICUIPanelState) => void;
  onPositionChange?: (position: ICUIPanelPosition) => void;
  onConfigChange?: (config: Partial<ICUIPanelConfig>) => void;
  onClose?: () => void;
  headerProps?: Partial<ICUIPanelHeaderProps>;
  contentProps?: Partial<ICUIPanelContentProps>;
}

export interface ICUIPanelActions {
  create: (config: ICUIPanelConfig) => ICUIPanelInstance;
  update: (id: string, updates: Partial<ICUIPanelInstance>) => void;
  remove: (id: string) => void;
  setState: (id: string, state: ICUIPanelState) => void;
  setPosition: (id: string, position: Partial<ICUIPanelPosition>) => void;
  setActive: (id: string) => void;
  clone: (id: string) => ICUIPanelInstance;
}

export interface ICUIPanelManagerState {
  panels: Record<string, ICUIPanelInstance>;
  activePanel: string | null;
  panelOrder: string[];
  defaultConfigs: Record<ICUIPanelType, Partial<ICUIPanelConfig>>;
}

export interface ICUIPanelHookResult {
  panels: ICUIPanelInstance[];
  activePanel: ICUIPanelInstance | null;
  actions: ICUIPanelActions;
  isLoading: boolean;
  error: string | null;
}
