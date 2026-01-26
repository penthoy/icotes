/**
 * Editor Module Exports
 * 
 * Central export point for all editor-related utilities and components
 */

// Types
export type { EditorFile, ICUIEditorRef } from './types';
export type { DiffMetadata, ProcessedDiff } from './utils/diffProcessor';

// Components
export { ImageViewerPanel } from './components/ImageViewerPanel';
export { PDFViewerPanel } from './components/PDFViewerPanel';
export { MediaPlayerPanel } from './components/MediaPlayerPanel';
export { EditorTabBar } from './components/EditorTabBar';
export { EditorActionBar } from './components/EditorActionBar';
export { LanguageSelectorModal } from './components/LanguageSelectorModal';

// Hooks
export { useFileOperations } from './hooks/useFileOperations';

// Utils
export { EditorNotificationService } from './utils/notifications';
export type { NotificationType } from './utils/notifications';

export { 
  detectFileTypeFromExtension,
  detectLanguageFromExtension, 
  getAvailableFileTypes,
  getAvailableLanguages,
  supportedFileTypes,
  supportedLanguages 
} from './utils/fileTypeDetection';
export type { FileTypeInfo, LanguageInfo } from './utils/fileTypeDetection';

export { processDiffPatch } from './utils/diffProcessor';
export { createEditorExtensions } from './utils/extensionsFactory';
