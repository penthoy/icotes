/**
 * Path utility functions for file operations
 */

/**
 * Format file path to show only the filename
 * @param filePath - Full file path
 * @returns Just the filename portion
 */
export const formatFilePath = (filePath: string): string => {
  if (!filePath) return 'Unknown file';
  // Normalize: strip file://, convert backslashes, trim trailing slashes
  const normalized = filePath.replace(/^file:\/\//, '').replace(/\\/g, '/').replace(/\/+$/, '');
  const parts = normalized.split('/').filter(Boolean);
  return parts[parts.length - 1] || 'Unknown file';
};

/**
 * Format file path for display, removing workspace prefix if present
 * @param path - Full file path  
 * @returns Cleaned path for display
 */
export const formatDisplayPath = (path: string): string => {
  if (!path) return 'Unknown file';

  // Normalize: strip file://, convert backslashes, trim trailing slashes
  const normalized = path.replace(/^file:\/\//, '').replace(/\\/g, '/').replace(/\/+$/, '');

  // Segment-aware: only treat 'workspace' as a path segment, not a substring.
  const wsParts = normalized.split('/').filter(Boolean);
  const wsIdx = wsParts.lastIndexOf('workspace');
  if (wsIdx !== -1) {
    const rel = wsParts.slice(wsIdx + 1).join('/');
    return rel || 'workspace';
  }

  const isAbsolute = normalized.startsWith('/') || /^[A-Za-z]:\//.test(normalized);
  if (isAbsolute) {
    const parts = normalized.split('/').filter(Boolean);
    // Try to find a meaningful starting point (like workspace, src, etc.)
    const meaningfulStarts = ['workspace', 'src', 'backend', 'frontend', 'docs'];
    const idx = parts.findIndex((seg) => meaningfulStarts.includes(seg));
    if (idx !== -1) {
      return parts.slice(idx).join('/');
    }
    // If no meaningful start found, return the filename and immediate parent (without leading slash)
    if (parts.length >= 2) {
      return parts.slice(-2).join('/');
    }
    return parts[0] || normalized;
  }
  
  return normalized;
};
/**
 * Get file extension from path
 * @param filePath - File path
 * @returns File extension (without dot) or empty string
 */
export const getFileExtension = (filePath: string): string => {
  if (!filePath) return '';
  const base = (filePath.split(/[\/\\]/).pop() || '').replace(/^\.+/, '');
  const idx = base.lastIndexOf('.');
  // No extension for dotfiles like '.env'  
  if (idx <= 0) return '';
  return base.slice(idx + 1).toLowerCase();
};

/**
 * Get directory path from file path
 * @param filePath - Full file path
 * @returns Directory path
 */
export const getDirectoryPath = (filePath: string): string => {
  if (!filePath) return '';
  const parts = filePath.split('/');
  return parts.slice(0, -1).join('/');
};

/**
 * Check if a path looks like a valid file path
 * @param path - Path to check
 * @returns True if it looks like a file path
 */
export const isValidFilePath = (path: string): boolean => {
  if (!path || typeof path !== 'string') return false;
  return path.includes('/') || path.includes('\\') || 
         /\.[a-zA-Z0-9]+$/.test(path); // Has file extension
};
