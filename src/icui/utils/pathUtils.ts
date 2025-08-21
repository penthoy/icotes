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
  const parts = filePath.split('/');
  return parts[parts.length - 1];
};

/**
 * Format file path for display, removing workspace prefix if present
 * @param path - Full file path  
 * @returns Cleaned path for display
 */
export const formatDisplayPath = (path: string): string => {
  if (!path) return 'Unknown file';
  
  // Remove common workspace prefixes
  if (path.startsWith('/home/penthoy/icotes/workspace/')) {
    return path.replace('/home/penthoy/icotes/workspace/', '');
  }
  if (path.startsWith('/home/penthoy/icotes/')) {
    return path.replace('/home/penthoy/icotes/', '');
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
  const parts = filePath.split('.');
  return parts.length > 1 ? parts.pop()?.toLowerCase() || '' : '';
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
