/**
 * ICUI Framework - Layout Type Definitions
 * A modular UI framework inspired by Blender's flexible panel system
 */

export interface ICUISize {
  width: number;
  height: number;
  minWidth?: number;
  minHeight?: number;
  maxWidth?: number;
  maxHeight?: number;
}

export interface ICUIPosition {
  x: number;
  y: number;
}

export interface ICUIBorder {
  top: boolean;
  right: boolean;
  bottom: boolean;
  left: boolean;
}

export interface ICUIResizeHandle {
  id: string;
  direction: 'horizontal' | 'vertical';
  position: ICUIPosition;
  active: boolean;
}

export interface ICUIFrameConfig {
  id: string;
  responsive: boolean;
  borderDetection: boolean;
  minPanelSize: ICUISize;
  resizeHandleSize: number;
  snapThreshold: number;
}

export interface ICUILayoutGrid {
  rows: number;
  columns: number;
  areas: string[][];
}

export interface ICUIViewport {
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

export type ICUIBreakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface ICUIResponsiveConfig {
  breakpoints: Record<ICUIBreakpoint, number>;
  currentBreakpoint: ICUIBreakpoint;
}
