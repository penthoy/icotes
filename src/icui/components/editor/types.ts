/**
 * Editor Type Definitions
 * 
 * TypeScript interfaces and types for the Editor component
 */

import { ICUIFile } from '../../services';

/**
 * Extended file interface with editor-specific properties
 */
export interface EditorFile extends ICUIFile {
  /** VS Code-like temporary file state (single-click opens as temporary) */
  isTemporary?: boolean;
  
  /** Diff metadata (only for diff virtual tabs) */
  __diffMeta?: {
    added: Set<number>;
    removed: Set<number>;
    hunk: Set<number>;
    originalPath?: string;
  };
}

/**
 * Ref interface for imperative control of the editor
 */
export interface ICUIEditorRef {
  /** Open a file in the editor (permanent) */
  openFile: (filePath: string) => Promise<void>;
  
  /** Open a file temporarily (single-click behavior) */
  openFileTemporary: (filePath: string) => Promise<void>;
  
  /** Open a file permanently (double-click behavior) */
  openFilePermanent: (filePath: string) => Promise<void>;
  
  /** Open a unified diff as read-only tab */
  openDiffPatch: (filePath: string) => Promise<void>;
}
