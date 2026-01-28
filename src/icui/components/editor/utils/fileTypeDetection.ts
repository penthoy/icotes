/**
 * File Type Detection Utilities
 * 
 * Detects file types from file extensions for proper handling in the editor.
 * Supports programming languages, documents, images, and multimedia files.
 * Used for syntax highlighting, file rendering, and determining the appropriate viewer.
 */

export interface FileTypeInfo {
  id: string;
  name: string;
}

export const supportedFileTypes: FileTypeInfo[] = [
  { id: 'python', name: 'Python' },
  { id: 'javascript', name: 'JavaScript' },
  { id: 'typescript', name: 'TypeScript' },
  { id: 'markdown', name: 'Markdown' },
  { id: 'json', name: 'JSON' },
  { id: 'html', name: 'HTML' },
  { id: 'css', name: 'CSS' },
  { id: 'yaml', name: 'YAML' },
  { id: 'shell', name: 'Shell/Bash' },
  { id: 'cpp', name: 'C++' },
  { id: 'rust', name: 'Rust' },
  { id: 'go', name: 'Go' },
  { id: 'text', name: 'Plain Text' },
  { id: 'image', name: 'Image' },
  { id: 'pdf', name: 'PDF Document' },
  { id: 'audio', name: 'Audio' },
  { id: 'video', name: 'Video' }
];

/**
 * Detects file type from file extension
 * @param filePath - Full path to the file
 * @returns File type ID string or null if unsupported
 */
export function detectFileTypeFromExtension(filePath: string): string | null {
  const fileName = filePath.split('/').pop() || '';
  const ext = fileName.includes('.') ? fileName.split('.').pop()?.toLowerCase() || '' : '';
  
  const fileTypeMap: Record<string, string> = {
    'py': 'python',
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'md': 'markdown',
    'json': 'json',
    'jsonl': 'json',
    'html': 'html',
    'htm': 'html',
    'css': 'css',
    'scss': 'css',
    'sass': 'css',
    'yaml': 'yaml',
    'yml': 'yaml',
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    'fish': 'shell',
    'cpp': 'cpp',
    'cxx': 'cpp',
    'cc': 'cpp',
    'c': 'cpp',
    'h': 'cpp',
    'hpp': 'cpp',
    'rs': 'rust',
    'go': 'go',
    'env': 'shell', // .env files use shell-like syntax
    'gitignore': 'shell', // .gitignore can use shell highlighting
    'txt': 'text', // Plain text files
    'log': 'text', // Log files as plain text
    // Image extensions
    'png': 'image',
    'jpg': 'image',
    'jpeg': 'image',
    'gif': 'image',
    'svg': 'image',
    'webp': 'image',
    'bmp': 'image',
    'ico': 'image',
    // PDF documents
    'pdf': 'pdf',
    // Audio extensions
    'mp3': 'audio',
    'wav': 'audio',
    'm4a': 'audio',
    'ogg': 'audio',
    // Video extensions
    'mp4': 'video',
    'mov': 'video',
    'webm': 'video'
  };
  
  // If no extension found (no dot in filename), treat as plain text
  if (!ext) {
    return 'text';
  }
  
  return fileTypeMap[ext] || null; // Return null for unsupported extensions
}

/**
 * Gets available file types for manual selection (primarily for code/text files)
 */
export function getAvailableFileTypes(): string[] {
  return [
    'text', 'python', 'javascript', 'typescript', 'markdown', 'json', 
    'html', 'css', 'yaml', 'shell', 'cpp', 'rust', 'go'
  ];
}

// Backward compatibility aliases - to be deprecated
/** @deprecated Use supportedFileTypes instead */
export const supportedLanguages = supportedFileTypes;
/** @deprecated Use FileTypeInfo instead */
export type LanguageInfo = FileTypeInfo;
/** @deprecated Use detectFileTypeFromExtension instead */
export const detectLanguageFromExtension = detectFileTypeFromExtension;
/** @deprecated Use getAvailableFileTypes instead */
export const getAvailableLanguages = getAvailableFileTypes;
