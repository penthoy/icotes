/**
 * Language Detection Utilities
 * 
 * Detects programming language/file type from file extensions
 * Used for syntax highlighting and file handling
 */

export interface LanguageInfo {
  id: string;
  name: string;
}

export const supportedLanguages: LanguageInfo[] = [
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
  { id: 'image', name: 'Image' }
];

/**
 * Detects language from file extension
 * @param filePath - Full path to the file
 * @returns Language ID string or null if unsupported
 */
export function detectLanguageFromExtension(filePath: string): string | null {
  const fileName = filePath.split('/').pop() || '';
  const ext = fileName.includes('.') ? fileName.split('.').pop()?.toLowerCase() || '' : '';
  
  const langMap: Record<string, string> = {
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
    'ico': 'image'
  };
  
  // If no extension found (no dot in filename), treat as plain text
  if (!ext) {
    return 'text';
  }
  
  return langMap[ext] || null; // Return null for unsupported extensions
}

/**
 * Gets available language options for manual selection
 */
export function getAvailableLanguages(): string[] {
  return [
    'text', 'python', 'javascript', 'typescript', 'markdown', 'json', 
    'html', 'css', 'yaml', 'shell', 'cpp', 'rust', 'go'
  ];
}
