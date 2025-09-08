/**
 * ICUI Menus Index
 * 
 * Centralized exports for all ICUI menu components
 */

// Deprecated: re-export archived FileMenu for tests/demos only
export { FileMenu } from '../archived/FileMenu_deprecate';
export type { 
  RecentFile,
  FileMenuProps,
  Project 
} from '../archived/FileMenu_deprecate';

export { LayoutMenu } from './LayoutMenu';
export type {
  LayoutMenuProps,
  PanelCreationOption,
  LayoutTemplate
} from './LayoutMenu';
 