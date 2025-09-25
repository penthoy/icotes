/**
 * ICUI Drag and Drop Types & Constants
 *
 * This module defines shared drag item payload contracts and custom
 * DOM event names used across panels (Explorer, Chat, future Notebook, etc.).
 *
 * The design goal is to keep the system lightweight (HTML5 DnD) while
 * providing a strongly-typed abstraction layer so additional drag sources
 * and drop targets can be added without rewriting core logic.
 */

// Custom MIME type for transferring explorer file selections
export const ICUI_FILE_LIST_MIME = 'application/x-icui-file-list';

// Custom DOM Events (bubble on window)
export const ICUI_DND_START_EVENT = 'icotes:dnd-start';
export const ICUI_DND_END_EVENT = 'icotes:dnd-end';
export const ICUI_DND_PREVIEW_REQUEST_EVENT = 'icotes:dnd-preview-request';

// Allowed drag item kinds (extensible)
export type DragItemKind = 'explorer:file' | 'explorer:folder' | 'explorer:multi' | 'external:file' | 'text' | 'unknown';

// Minimal descriptor for a file/folder node (kept framework agnostic)
export interface DragFileDescriptor {
  path: string;      // absolute path
  name: string;      // filename or folder name
  type: 'file' | 'folder';
}

// Payload stored in DataTransfer under ICUI_FILE_LIST_MIME
export interface ExplorerDragPayload {
  kind: DragItemKind;
  paths: string[];              // absolute paths for all dragged items
  items: DragFileDescriptor[];  // descriptors (used by chat, agents, etc.)
  multi: boolean;               // convenience flag (paths.length > 1)
  ts: number;                   // timestamp for debugging / correlation
}

// Detail dispatched with icotes:dnd-start event
export interface DragStartDetail extends ExplorerDragPayload {
  source: 'explorer' | 'chat' | 'external' | string; // panel/source identifier
}

// Detail dispatched with icotes:dnd-end event
export interface DragEndDetail {
  cancelled?: boolean; // reserved for future logic (escape cancel, etc.)
  ts: number;          // timestamp matching original drag start if needed
}

export function isExplorerPayload(value: any): value is ExplorerDragPayload {
  return value && Array.isArray(value.paths) && Array.isArray(value.items);
}
