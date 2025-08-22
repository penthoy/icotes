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
  
  // Fallback: remove common workspace prefixes (browser-safe approach)
  // Look for common icotes workspace patterns
  if (path.includes('/workspace/')) {
    const workspaceIndex = path.lastIndexOf('/workspace/');
    return path.substring(workspaceIndex + 11); // Remove '/workspace/' prefix
  }
  
  // Fallback: remove any absolute path prefix and show relative path
  if (path.startsWith('/')) {
    const parts = path.split('/');
    // Try to find a meaningful starting point (like workspace, src, etc.)
    const meaningfulStarts = ['workspace', 'src', 'backend', 'frontend', 'docs'];
    for (let i = 0; i < parts.length; i++) {
      if (meaningfulStarts.includes(parts[i])) {
        return parts.slice(i).join('/');
      }
    }
    // If no meaningful start found, just return the filename and immediate parent
    return parts.slice(-2).join('/');
  }
  
  return path;
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
