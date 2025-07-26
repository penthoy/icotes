/**
 * ICUI Framework - Main Entry Point
 * This is the main entry point for the ICUI framework
 * It exports all the components, layouts, and utilities
 */

// Components
export { ICUIFrameContainer } from './components/ICUIFrameContainer';
export { ICUISplitPanel } from './components/ICUISplitPanel';
export { ICUILayoutPresetSelector } from './components/ICUILayoutPresetSelector';
export { ICUIBasePanel } from './components/ICUIBasePanel';
export { ICUIPanelHeader } from './components/ICUIPanelHeader';
export { ICUIPanelContent } from './components/ICUIPanelContent';
export { ICUIPanelArea } from './components/ICUIPanelArea';
export { default as ICUITabContainer } from './components/ICUITabContainer';
export { ICUIEnhancedLayout } from './components/ICUIEnhancedLayout';

// Core Components (Main ICUI interface components)
export { default as ICUIChat } from './components/ICUIChat';
export { default as ICUITerminal } from './components/ICUITerminal';
export { default as ICUIEditor } from './components/ICUIEditor';
export { default as ICUIExplorer } from './components/ICUIExplorer';

// Core Component Types
export type { ICUIChatRef } from './components/ICUIChat';
export type { ICUITerminalRef } from './components/ICUITerminal';
export type { ICUIEditorRef } from './components/ICUIEditor';

// Base Layout Components
export { ICUIBaseHeader } from './components/ICUIBaseHeader';
export { ICUIBaseFooter } from './components/ICUIBaseFooter';

// Enhanced Components (New)
// export { ICUITest1, ICUITest2, ICUITest3, ICUITest4, ICUITest5, ICUITest6, ICUITest7, ICUITest8, ICUITest9, ICUITest10 } from './tests';

// Enhanced Panels
export { default as ICUIEnhancedEditorPanel } from './components/panels/ICUIEnhancedEditorPanel';
export { default as ICUIEnhancedEditorPanelOld } from './components/panels/ICUIEnhancedEditorPanelOld';
export { default as ICUIEditorPanelFromScratch } from './components/panels/ICUIEditorPanelFromScratch';
export { default as ICUIEnhancedTerminalPanel } from './components/panels/ICUIEnhancedTerminalPanel';

// Original Specialized Panels
export { default as ICUITerminalPanel } from './components/panels/ICUITerminalPanel';
export { default as ICUIEditorPanel } from './components/panels/ICUIEditorPanel';
export { default as ICUIExplorerPanel } from './components/panels/ICUIExplorerPanel';
export { default as ICUIChatPanel } from './components/panels/ICUIChatPanel';

// Hooks
export { useICUIResponsive } from './hooks/icui-use-responsive';
export { useICUILayoutState, useCurrentLayout, useLayoutPresets } from './hooks/icui-use-layout-state';
export { useICUIPanels, createPanel, PanelUtils } from './hooks/icui-use-panels';
export { useChatMessages } from './hooks/useChatMessages';
export type { 
  UseChatMessagesOptions, 
  UseChatMessagesReturn 
} from './hooks/useChatMessages';
export { useTheme } from './hooks/useTheme';
export type { ThemeState } from './hooks/useTheme';

// Types
export type {
  ICUISize,
  ICUIPosition,
  ICUIBorder,
  ICUIResizeHandle,
  ICUIFrameConfig,
  ICUILayoutGrid,
  ICUIViewport,
  ICUIBreakpoint,
  ICUIResponsiveConfig,
} from './types/icui-layout';

// Chat Types
export * from './types/chatTypes';

// Services
export { ChatBackendClient } from './services/chatBackendClient';
export { notificationService, useNotifications } from './services/notificationService';
export type { 
  NotificationType, 
  NotificationOptions, 
  Notification 
} from './services/notificationService';

// Utilities
export * from './utils/urlHelpers';

export type {
  ICUISplitDirection,
  ICUISplitMode,
  ICUISplitConfig,
  ICUISplitPanelState,
  ICUISplitHandle,
  ICUISplitPanelProps,
} from './types/icui-split';

export type {
  ICUILayoutPresetType,
  ICUILayoutState,
  ICUIPanelState,
  ICUILayoutPreset,
  ICUILayoutManagerState,
  ICUILayoutActions,
  ICUILayoutPersistence,
  ICUILayoutHookResult,
} from './types/icui-layout-state';

export type {
  ICUIPanelType,
  ICUIPanelState as ICUIPanelInstanceState,
  ICUIPanelContentType,
  ICUIPanelConfig,
  ICUIPanelContextMenuItem,
  ICUIPanelPosition,
  ICUIPanelInstance,
  ICUIPanelHeaderProps,
  ICUIPanelContentProps,
  ICUIBasePanelProps,
  ICUIPanelActions,
  ICUIPanelManagerState,
  ICUIPanelHookResult,
} from './types/icui-panel';

// Enhanced Component Types
export type {
  ICUILayoutArea,
  ICUILayoutConfig,
  ICUIEnhancedLayoutProps,
} from './components/ICUIEnhancedLayout';

export type {
  ICUIEnhancedPanel,
  ICUIEnhancedPanelAreaProps,
} from './components/ICUIEnhancedPanelArea';

export type {
  ICUITab,
  ICUITabContainerProps,
} from './components/ICUITabContainer';

export type {
  ICUIEditorFile,
  ICUIEnhancedEditorPanelProps,
} from './components/panels/ICUIEnhancedEditorPanel';

// Base Layout Component Types
export type {
  ICUIBaseHeaderProps,
  ICUIMenuProps,
  ICUIBaseHeaderState,
} from './components/ICUIBaseHeader';

export type {
  ICUIBaseFooterProps,
} from './components/ICUIBaseFooter';

// Version
export const ICUI_VERSION = '4.0.0';

// Framework info
export const ICUI_INFO = {
  name: 'ICUI Framework',
  version: ICUI_VERSION,
  description: 'Interactive Component UI Framework - Modular panel system inspired by Blender',
  author: 'Generated by AI Assistant',
  license: 'MIT',
};
