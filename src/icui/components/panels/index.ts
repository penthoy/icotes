// ICUI Panel Components - Main functional panels
export { default as ICUIChat } from './ICUIChat';
export { default as ICUIChatHistory } from './ICUIChatHistory';
export { default as ICUIEditor } from './ICUIEditor';
export { default as ICUIExplorer } from './ICUIExplorer';
export { default as ICUITerminal } from './ICUITerminal';
export { default as ICUIGit } from './ICUIGit';

// Export types
export type { ICUIEditorRef } from './ICUIEditor';
export type { ICUITerminalRef } from './ICUITerminal';
export type { ICUIChatRef } from './ICUIChat';

// DEPRECATED: Legacy panel wrappers - kept for backward compatibility
export { default as ICUITerminalPanel } from '../archived/ICUITerminalPanel_deprecate';
export { default as ICUIEditorPanel } from '../archived/ICUIEditorPanel_deprecate';
export { default as ICUIChatPanel } from '../archived/ICUIChatPanel_deprecate';
export { default as ICUIExplorerPanel } from '../archived/ICUIExplorerPanel_deprecate'; 