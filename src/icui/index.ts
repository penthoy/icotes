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
export { ICUILayout } from './components/ICUILayout';
export { ICUIEnhancedLayout } from './components/archived/ICUIEnhancedLayout_deprecated'; // @deprecated - use ICUILayout

// Core Components (Main ICUI interface components) - moved to panels
export { default as ICUIChat } from './components/panels/ICUIChat';
export { default as ICUITerminal } from './components/panels/ICUITerminal';
export { default as ICUIEditor } from './components/panels/ICUIEditor';
export { default as ICUIExplorer } from './components/panels/ICUIExplorer';
export { default as ICUIChatHistory } from './components/panels/ICUIChatHistory';
export { default as ICUIGit } from './components/panels/ICUIGit';
export { default as ICUIPreview } from './components/panels/ICUIPreview';

// Core Component Types
export type { ICUIChatRef } from './components/panels/ICUIChat';
export type { ICUITerminalRef } from './components/panels/ICUITerminal';
export type { ICUIEditorRef } from './components/panels/ICUIEditor';
export type { ICUIPreviewRef } from './components/panels/ICUIPreview';

// Base Layout Components
export { ICUIBaseHeader } from './components/ICUIBaseHeader';
export { ICUIBaseFooter } from './components/ICUIBaseFooter';

// Enhanced Components (New)
// export { ICUITest1, ICUITest2, ICUITest3, ICUITest4, ICUITest5, ICUITest6, ICUITest7, ICUITest8, ICUITest9, ICUITest10 } from './tests';

// Primary Panels (formerly Enhanced) - DEPRECATED: Moved to archived
export { default as ICUITerminalPanel } from './components/archived/ICUITerminalPanel_deprecate';
export { default as ICUIEditorPanel } from './components/archived/ICUIEditorPanel_deprecate';
export { default as ICUIExplorerPanel } from './components/archived/ICUIExplorerPanel_deprecate';
export { default as ICUIChatPanel } from './components/archived/ICUIChatPanel_deprecate';

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

// Layout Component Types
export type {
  ICUILayoutArea,
  ICUILayoutConfig,
  ICUILayoutProps,
} from './components/ICUILayout';

// @deprecated - use types from ICUILayout instead
export type {
  ICUILayoutArea as ICUILayoutAreaDeprecated,
  ICUILayoutConfig as ICUILayoutConfigDeprecated,
  ICUIEnhancedLayoutProps,
} from './components/archived/ICUIEnhancedLayout_deprecated';

export type {
  ICUIPanel,
  ICUIPanelAreaProps,
} from './components/ICUIPanelArea';

export type {
  ICUITab,
  ICUITabContainerProps,
} from './components/ICUITabContainer';

export type {
  ICUIEditorFile,
  ICUIEditorPanelProps,
} from './components/archived/ICUIEditorPanel_deprecate';

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
  description: 'Interactive Component UI Framework - Modular panel system',
  author: 'icotes.com',
  license: 'Apache-2.0',
};
