/**
 * Workspace Utilities for ICUI Components
 * 
 * Centralized workspace path resolution and utilities.
 * Eliminates code duplication across ICUIEditor, ICUIExplorer, ICUITerminal.
 */

/**
 * Get the configured workspace root path
 * Throws an error if VITE_WORKSPACE_ROOT is not configured
 */
export const getWorkspaceRoot = (): string => {
  const workspaceRoot = (import.meta as any).env?.VITE_WORKSPACE_ROOT;
  if (!workspaceRoot) {
    throw new Error(
      'VITE_WORKSPACE_ROOT environment variable is not configured. ' +
      'Please ensure your .env file contains VITE_WORKSPACE_ROOT=/path/to/workspace'
    );
  }
  return workspaceRoot;
};

/**
 * Resolve a relative path within the workspace
 */
export const resolveWorkspacePath = (relativePath: string): string => {
  const root = getWorkspaceRoot();
  return `${root}/${relativePath}`.replace(/\/+/g, '/');
};

/**
 * Check if a path is within the workspace
 */
export const isWorkspacePath = (path: string): boolean => {
  const root = getWorkspaceRoot();
  return path.startsWith(root);
};

/**
 * Get relative path from workspace root
 */
export const getRelativeWorkspacePath = (absolutePath: string): string => {
  const root = getWorkspaceRoot();
  if (absolutePath.startsWith(root)) {
    return absolutePath.substring(root.length).replace(/^\/+/, '');
  }
  return absolutePath;
};

/**
 * Normalize workspace path (resolve .. and . components)
 */
export const normalizeWorkspacePath = (path: string): string => {
  // Simple path normalization - in a real app you might want a more robust solution
  return path
    .split('/')
    .reduce((acc: string[], part: string) => {
      if (part === '..') {
        acc.pop();
      } else if (part && part !== '.') {
        acc.push(part);
      }
      return acc;
    }, [])
    .join('/');
};

/**
 * Get file extension from path
 */
export const getFileExtension = (path: string): string => {
  return path.split('.').pop()?.toLowerCase() || '';
};

/**
 * Check if path represents a file (has extension) vs directory
 */
export const isFile = (path: string): boolean => {
  const parts = path.split('/');
  const lastPart = parts[parts.length - 1];
  return lastPart.includes('.');
};

/**
 * Get directory path from file path
 */
export const getDirectoryPath = (filePath: string): string => {
  const parts = filePath.split('/');
  parts.pop(); // Remove filename
  return parts.join('/') || '/';
};

/**
 * Get filename from path
 */
export const getFileName = (path: string): string => {
  return path.split('/').pop() || '';
};
