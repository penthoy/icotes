/**
 * ICUI Framework - Split Panel Type Definitions
 * Additional types for the split panel system
 */

export type ICUISplitDirection = 'horizontal' | 'vertical';
export type ICUISplitMode = 'split' | 'collapsed' | 'expanded';

export interface ICUISplitConfig {
  id: string;
  direction: ICUISplitDirection;
  initialSplit: number; // Percentage (0-100)
  minSize: number; // Minimum size in pixels
  maxSize?: number; // Maximum size in pixels
  collapsible: boolean;
  resizable: boolean;
  snapThreshold: number;
}

export interface ICUISplitPanelState {
  splitPercentage: number;
  isFirstPanelCollapsed: boolean;
  isSecondPanelCollapsed: boolean;
  isDragging: boolean;
  dragStartPosition: number;
  dragStartSplit: number;
}

export interface ICUISplitHandle {
  id: string;
  direction: ICUISplitDirection;
  position: number; // Position as percentage
  active: boolean;
  size: number; // Handle size in pixels
}

export interface ICUISplitPanelProps {
  id: string;
  config?: Partial<ICUISplitConfig>;
  className?: string;
  style?: React.CSSProperties;
  onSplitChange?: (splitPercentage: number) => void;
  onPanelCollapse?: (panel: 'first' | 'second', collapsed: boolean) => void;
  firstPanel: React.ReactNode;
  secondPanel: React.ReactNode;
}
