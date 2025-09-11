/**
 * ICUI Editor Component
 * 
 * Updated to use centralized backend service and workspace utilities.
 * This eliminates code duplication and provides consistent behavior.
 * 
 * Key Features:
 * - Centralized backend service for file operations
 * - Multi-file tabs with bac      const newStatus = {
        connected: false,
        error: (error as Error).message || 'Unknown error',
        timestamp: Date.now()
      };
      // Backend connection error
      setConnectionStatus(newStatus);
      if (onConnectionStatusChange) {
        // Calling onConnectionStatusChange callback with error
        onConnectionStatusChange(newStatus);
      } else {
        // No onCon  const activateFile = useCallback(async (fileId: string) => {
    // console.log('Activating file:', fileId);ctionStatusChange callback available
      }zation
 * - Auto-save with debouncing
 * - Real-time file loading from backend
 * - CodeMirror 6 integration with syntax highlighting
 * - Theme detection and workspace root integration
 * - Error handling and connection status display
 */

import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import {
  EditorView,
  keymap,
  lineNumbers,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
  ViewPlugin,
  Decoration,
  ViewUpdate
} from "@codemirror/view";
import { EditorState, Extension } from "@codemirror/state";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { backendService, ICUIFile, useTheme, ConnectionStatus } from '../../services';
import { getWorkspaceRoot } from '../../lib';
import {
  autocompletion,
  completionKeymap,
  closeBrackets,
  closeBracketsKeymap,
} from "@codemirror/autocomplete";
import {
  syntaxHighlighting,
  indentOnInput,
  bracketMatching,
  foldKeymap,
  foldGutter,
} from "@codemirror/language";
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { markdown } from '@codemirror/lang-markdown';
import { json } from '@codemirror/lang-json';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { cpp } from '@codemirror/lang-cpp';
import { rust } from '@codemirror/lang-rust';
import { go } from '@codemirror/lang-go';
import { StreamLanguage } from '@codemirror/language';
import { yaml } from '@codemirror/legacy-modes/mode/yaml';
import { shell } from '@codemirror/legacy-modes/mode/shell';
import { createICUISyntaxHighlighting, createICUIEnhancedEditorTheme } from '../../utils/syntaxHighlighting';

// File interface (using centralized ICUIFile type)
interface EditorFile extends ICUIFile {
  isTemporary?: boolean; // VS Code-like temporary file state
  // Diff metadata (only for diff virtual tabs)
  __diffMeta?: {
    added: Set<number>;
    removed: Set<number>;
    hunk: Set<number>;
    originalPath?: string;
  };
}



// Notification system (following simpleeditor pattern)
class EditorNotificationService {
  static show(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info'): void {
    const notification = document.createElement('div');
    const colors = {
      success: 'bg-green-500 text-white',
      error: 'bg-red-500 text-white',
      warning: 'bg-yellow-500 text-black',
      info: 'bg-blue-500 text-white'
    };
    
    notification.className = `fixed top-4 right-4 px-4 py-2 rounded shadow-lg z-50 transition-opacity ${colors[type]}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }
}

// Ref interface for imperative control
interface ICUIEditorRef {
  openFile: (filePath: string) => Promise<void>;
  openFileTemporary: (filePath: string) => Promise<void>;
  openFilePermanent: (filePath: string) => Promise<void>;
  openDiffPatch: (filePath: string) => Promise<void>; // Phase 4: open unified diff as read-only tab
}

interface ICUIEditorProps {
  className?: string;
  files?: EditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, newContent: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileReorder?: (fromIndex: number, toIndex: number) => void;
  onConnectionStatusChange?: (status: ConnectionStatus) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
  workspaceRoot?: string;
}

const ICUIEditor = forwardRef<ICUIEditorRef, ICUIEditorProps>(({
  className = '',
  files: propFiles = [],
  activeFileId: propActiveFileId,
  onFileChange,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  onFileActivate,
  onFileReorder,
  onConnectionStatusChange,
  autoSave = false,
  autoSaveDelay = 1500,
  workspaceRoot
}, ref) => {
  // State management (following simpleeditor pattern)
  const [files, setFiles] = useState<EditorFile[]>(propFiles);
  const [activeFileId, setActiveFileId] = useState<string>(propActiveFileId || '');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(false); // Always default to false regardless of prop
  const [showLanguageSelector, setShowLanguageSelector] = useState(false);
  const [currentFileForLanguageSelect, setCurrentFileForLanguageSelect] = useState<string | null>(null);
  
  // Language fallback selector
  const [showLanguageFallback, setShowLanguageFallback] = useState(false);
  const [pendingFile, setPendingFile] = useState<{ file: any; filePath: string } | null>(null);
  
  const supportedLanguages = [
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
    { id: 'text', name: 'Plain Text' }
  ];

  // Refs (following ICUIEnhancedEditorPanel pattern)
  const editorRef = useRef<HTMLDivElement>(null);
  const editorViewRef = useRef<EditorView | null>(null);
  const activeFileIdRef = useRef<string>('');
  const saveHandlerRef = useRef<() => void | Promise<void>>(() => {});
  // Use centralized theme service instead of manual theme detection
  const { theme } = useTheme();
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentContentRef = useRef<string>(''); // Track current content to prevent loops
  const contentChangeHandlerRef = useRef<((content: string) => void) | null>(null); // Stable ref for content changes

  // Get workspace root from environment (following ICUIExplorer pattern)
  const effectiveWorkspaceRoot = workspaceRoot || getWorkspaceRoot();

  // Helper function to detect language from file extension
  const detectLanguageFromExtension = useCallback((filePath: string): string | null => {
    const ext = filePath.split('.').pop()?.toLowerCase() || '';
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
      '': 'text' // Files without extension
    };
    return langMap[ext] || null; // Return null for unsupported extensions
  }, []);

  // Helper function to get available language options for fallback
  const getAvailableLanguages = () => [
    'text', 'python', 'javascript', 'typescript', 'markdown', 'json', 
    'html', 'css', 'yaml', 'shell', 'cpp', 'rust', 'go'
  ];

  // Helper function to handle language fallback selection
  const handleLanguageFallback = useCallback((selectedLanguage: string) => {
    if (pendingFile) {
      const { file, filePath } = pendingFile;
      const fileWithLanguage = { ...file, language: selectedLanguage };
      
  // Check if a NON-diff version of the file is already open (ignore diff tabs sharing path)
  const existingFileIndex = files.findIndex(f => f.path === filePath && !(f as any).isDiff);
      if (existingFileIndex >= 0) {
        // File is already open, just activate it and update language
        setFiles(prev => prev.map((f, index) => 
          index === existingFileIndex ? { ...f, isTemporary: file.isTemporary || false, language: selectedLanguage } : f
        ));
        setActiveFileId(files[existingFileIndex].id);
      } else {
        // Add new file to the list
        if (file.isTemporary) {
          // Handle temporary file - remove other temporary files first
          setFiles(prev => [...prev.filter(f => !f.isTemporary), fileWithLanguage]);
        } else {
          // Handle permanent file
          setFiles(prev => [...prev, fileWithLanguage]);
        }
        setActiveFileId(fileWithLanguage.id);
      }
      
      const languageName = supportedLanguages.find(l => l.id === selectedLanguage)?.name || selectedLanguage;
      const fileTypeMsg = file.isTemporary ? ' (temporary)' : '';
      EditorNotificationService.show(`Opened ${fileWithLanguage.name}${fileTypeMsg} with ${languageName} highlighting`, 'success');
    }
    
    // Clean up
    setShowLanguageFallback(false);
    setPendingFile(null);
  }, [files, pendingFile, supportedLanguages]);

  // File opening methods for external control (e.g., from Explorer)
  const openFile = useCallback(async (filePath: string) => {
    try {
      setIsLoading(true);
      const fileData = await backendService.getFile(filePath);
      
      // Auto-detect language from file extension
      const detectedLanguage = detectLanguageFromExtension(filePath);
      
      if (detectedLanguage === null) {
        // Show language fallback selector for unsupported extensions
        setPendingFile({ file: fileData, filePath });
        setShowLanguageFallback(true);
        setIsLoading(false);
        return;
      }
      
      const fileWithLanguage = { ...fileData, language: detectedLanguage };
      
  // Check if a NON-diff version of the file is already open (ignore diff tabs sharing path)
  const existingFileIndex = files.findIndex(f => f.path === filePath && !(f as any).isDiff);
      if (existingFileIndex >= 0) {
        // File is already open, just activate it and mark as permanent
        setFiles(prev => prev.map((f, index) => 
          index === existingFileIndex ? { ...f, isTemporary: false, language: detectedLanguage } : f
        ));
        setActiveFileId(files[existingFileIndex].id);
      } else {
        // Add new file to the list as permanent
        const permanentFile = { ...fileWithLanguage, isTemporary: false };
        setFiles(prev => [...prev, permanentFile]);
        setActiveFileId(permanentFile.id);
      }
      
      EditorNotificationService.show(`Opened ${fileWithLanguage.name}`, 'success');
    } catch (error) {
      console.error('Failed to open file:', error);
      EditorNotificationService.show(`Failed to open ${filePath}: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files, detectLanguageFromExtension]);

  const openFileTemporary = useCallback(async (filePath: string) => {
    try {
      setIsLoading(true);
      
      // Check if file is already open
      const existingFileIndex = files.findIndex(f => f.path === filePath);
      if (existingFileIndex >= 0) {
        // File is already open, just activate it
        const existingFile = files[existingFileIndex];
        setActiveFileId(existingFile.id);
        return;
      }

      // VS Code behavior: Only replace existing temporary files, not permanent ones
      const temporaryFiles = files.filter(f => f.isTemporary);
      if (temporaryFiles.length > 0) {
        // Remove all temporary files since we're opening a new temporary file
        setFiles(prev => prev.filter(f => !f.isTemporary));
      }

      // Load the new file and mark it as temporary
      const fileData = await backendService.getFile(filePath);
      const detectedLanguage = detectLanguageFromExtension(filePath);
      
      if (detectedLanguage === null) {
        // Show language fallback selector for unsupported extensions
        setPendingFile({ file: { ...fileData, isTemporary: true }, filePath });
        setShowLanguageFallback(true);
        setIsLoading(false);
        return;
      }
      
      const temporaryFile = { ...fileData, language: detectedLanguage, isTemporary: true };
      
      // Add new temporary file to the list (keeping all permanent files)
      setFiles(prev => [...prev.filter(f => !f.isTemporary), temporaryFile]);
      setActiveFileId(temporaryFile.id);
      
      EditorNotificationService.show(`Opened ${temporaryFile.name} (temporary)`, 'info');
    } catch (error) {
      console.error('Failed to open temporary file:', error);
      EditorNotificationService.show(`Failed to open ${filePath}: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files]);

  const openFilePermanent = useCallback(async (filePath: string) => {
    await openFile(filePath);
  }, [openFile]);

  // Open synthetic diff (for untracked files)
  const openSyntheticDiff = useCallback(async (filePath: string, patch: string) => {
    console.log('[ICUIEditor] openSyntheticDiff called for:', filePath);
    try {
      setIsLoading(true);
      const tabId = `diff:${filePath}`;
      const existingIdx = files.findIndex(f => f.id === tabId);
      if (existingIdx >= 0) {
        console.log('[ICUIEditor] Synthetic diff tab already exists, focusing:', tabId);
        setActiveFileId(tabId);
        return;
      }
      const name = `${filePath.split('/').pop() || filePath} (diff)`;
      console.log('[ICUIEditor] Creating new synthetic diff tab:', name);

      // Process synthetic diff for highlighting
      const rawLines = patch.split('\n');
      const added = new Set<number>();
      const hunk = new Set<number>();
      const processed: string[] = [];
      for (const line of rawLines) {
        if (line.startsWith('+++ ') || line.startsWith('--- ') || line.startsWith('index ') || line.startsWith('diff ') || line.startsWith('new file mode')) {
          processed.push(line); // keep file headers as-is
          continue;
        }
        if (line.startsWith('@@')) {
          hunk.add(processed.length + 1);
          processed.push(line); // keep hunk header
          continue;
        }
        if (line.startsWith('+') && !line.startsWith('+++ ')) {
          added.add(processed.length + 1);
          processed.push(line.slice(1));
          continue;
        }
        processed.push(line); // fallback
      }
      const processedPatch = processed.join('\n');
      const diffFile: EditorFile = {
        id: tabId,
        name,
        language: 'diff',
        content: processedPatch,
        modified: false,
        path: filePath,
        // @ts-ignore add virtual flags
        isDiff: true,
        // @ts-ignore
        readOnly: true,
        // @ts-ignore
        diffKind: 'synthetic',
        // @ts-ignore
        originalPath: filePath,
        __diffMeta: { added, removed: new Set(), hunk, originalPath: filePath }
      } as any;
      setFiles(prev => [...prev, diffFile]);
      setActiveFileId(tabId);
      console.log('[ICUIEditor] Synthetic diff tab created successfully');
      EditorNotificationService.show(`Opened diff for ${filePath}`, 'info');
    } catch (error) {
      console.error('Failed to open synthetic diff:', error);
      EditorNotificationService.show(`Failed to open diff: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files]);

  // Phase 4: Open unified diff patch for a file as a virtual read-only tab
  const openDiffPatch = useCallback(async (filePath: string) => {
    console.log('[ICUIEditor] openDiffPatch called for:', filePath);
    try {
      setIsLoading(true);
      // Reuse existing diff endpoint
      console.log('[ICUIEditor] Fetching diff from backend...');
      const diffData = await backendService.getScmDiff(filePath);
      console.log('[ICUIEditor] Diff data received:', diffData);
      if (!diffData || typeof diffData.patch !== 'string') {
        console.warn('[ICUIEditor] No valid diff data:', diffData);
        EditorNotificationService.show(`No diff available for ${filePath}`, 'warning');
        return;
      }
      const tabId = `diff:${filePath}`;
      const existingIdx = files.findIndex(f => f.id === tabId);
      if (existingIdx >= 0) {
        console.log('[ICUIEditor] Diff tab already exists, focusing:', tabId);
        setActiveFileId(tabId);
        return;
      }
      const name = `${filePath.split('/').pop() || filePath} (diff)`;
      console.log('[ICUIEditor] Creating new diff tab:', name);

      // Preprocess unified diff for improved syntax highlighting:
      // - Strip leading diff markers (+, -, space) from code lines
      // - Record line numbers for added/removed/hunk to apply background decorations
      const rawLines = diffData.patch.split('\n');
      const added = new Set<number>();
      const removed = new Set<number>();
      const hunk = new Set<number>();
      const processed: string[] = [];
      for (const line of rawLines) {
        if (line.startsWith('+++ ') || line.startsWith('--- ') || line.startsWith('index ') || line.startsWith('diff ')) {
          processed.push(line); // keep file headers as-is
          continue;
        }
        if (line.startsWith('@@')) {
          hunk.add(processed.length + 1);
          processed.push(line); // keep hunk header
          continue;
        }
        if (line.startsWith('+') && !line.startsWith('+++ ')) {
          added.add(processed.length + 1);
          processed.push(line.slice(1));
          continue;
        }
        if (line.startsWith('-') && !line.startsWith('--- ')) {
          removed.add(processed.length + 1);
          processed.push(line.slice(1));
          continue;
        }
        if (line.startsWith(' ')) {
          processed.push(line.slice(1)); // unchanged line (unified diff prefix space)
          continue;
        }
        processed.push(line); // fallback
      }
      const processedPatch = processed.join('\n');
      const diffFile: EditorFile = {
        id: tabId,
        name,
        language: 'diff',
        content: processedPatch,
        modified: false,
        path: filePath,
        // @ts-ignore add virtual flags
        isDiff: true,
        // @ts-ignore
        readOnly: true,
        // @ts-ignore
        diffKind: 'patch',
        // @ts-ignore
        originalPath: filePath,
        __diffMeta: { added, removed, hunk, originalPath: filePath }
      } as any;
      setFiles(prev => [...prev, diffFile]);
      setActiveFileId(tabId);
      console.log('[ICUIEditor] Diff tab created successfully');
      EditorNotificationService.show(`Opened diff for ${filePath}`, 'info');
    } catch (error) {
      console.error('Failed to open diff patch:', error);
      EditorNotificationService.show(`Failed to open diff: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files]);

  // Listen for global diff open events (fallback when panel prop not passed)
  useEffect(() => {
    const handler = (e: any) => {
      const path = e?.detail?.path;
      if (typeof path === 'string') {
        console.log('[ICUIEditor] Received global icui:openDiffPatch event for', path);
        openDiffPatch(path);
      }
    };
    
    const syntheticHandler = (e: any) => {
      const { path, patch } = e?.detail || {};
      if (typeof path === 'string' && typeof patch === 'string') {
        console.log('[ICUIEditor] Received synthetic diff event for', path);
        openSyntheticDiff(path, patch);
      }
    };
    
    window.addEventListener('icui:openDiffPatch', handler as any);
    window.addEventListener('icui:openSyntheticDiff', syntheticHandler as any);
    return () => {
      window.removeEventListener('icui:openDiffPatch', handler as any);
      window.removeEventListener('icui:openSyntheticDiff', syntheticHandler as any);
    };
  }, [openDiffPatch, openSyntheticDiff]);

  // Expose methods via ref for external control
  useImperativeHandle(ref, () => ({
    openFile,
    openFileTemporary, 
    openFilePermanent,
    openDiffPatch
  }), [openFile, openFileTemporary, openFilePermanent, openDiffPatch]);

  // Theme detection (following ICUITerminal pattern with all themes)
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    
    const detectTheme = () => {
      // Debounce theme detection to prevent rapid changes
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        const htmlElement = document.documentElement;
        const isDark = htmlElement.classList.contains('dark') || 
                       htmlElement.classList.contains('icui-theme-github-dark') ||
                       htmlElement.classList.contains('icui-theme-monokai') ||
                       htmlElement.classList.contains('icui-theme-one-dark') ||
                       htmlElement.classList.contains('icui-theme-dracula') ||
                       htmlElement.classList.contains('icui-theme-solarized-dark');
        setIsDarkTheme(isDark);
      }, 50); // 50ms debounce
    };

    detectTheme();
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => {
      clearTimeout(timeoutId);
      observer.disconnect();
    };
  }, []);

  // Backend connection check using centralized service
  const checkBackendConnection = useCallback(async () => {
    try {
      const status = await backendService.getConnectionStatus();
      const newStatus = {
        connected: status.connected,
        timestamp: Date.now()
      };
      // Backend connection status updated
      setConnectionStatus(newStatus);
      if (onConnectionStatusChange) {
        // Calling onConnectionStatusChange callback
        onConnectionStatusChange(newStatus);
      } else {
        // No onConnectionStatusChange callback available
      }
      return status.connected;
    } catch (error) {
      const newStatus = {
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      };
      // Backend connection error
      setConnectionStatus(newStatus);
      if (onConnectionStatusChange) {
        // Calling onConnectionStatusChange callback with error
        onConnectionStatusChange(newStatus);
      } else {
        // No onConnectionStatusChange callback available
      }
      return false;
    }
  }, []); // Remove onConnectionStatusChange from dependencies to prevent infinite loops

  // Load files from workspace (following simpleeditor pattern)
  const loadFiles = useCallback(async () => {
    if (!connectionStatus.connected) return;
    
    setIsLoading(true);
    try {
      // Loading files from workspace
      // First, get the list of files without content
      const loadedFiles = await backendService.getWorkspaceFiles(effectiveWorkspaceRoot);
      // Loaded file list
      
      if (loadedFiles.length > 0) {
        // Load content for the first file immediately before setting files
        try {
          // Loading content for first file
          const fileWithContent = await backendService.getFile(loadedFiles[0].path!);
          // Loaded content for first file
          
          // Update the first file with content
          loadedFiles[0] = { ...loadedFiles[0], content: fileWithContent.content };
        } catch (error) {
          console.warn(`Failed to load content for ${loadedFiles[0].name}:`, error);
        }
        
        // Set files list with first file content loaded
        setFiles(loadedFiles);
        
        // Set the first file as active if no active file is set
        if (!activeFileId) {
          // Setting active file to first file
          setActiveFileId(loadedFiles[0].id);
        }
      } else {
        setFiles(loadedFiles);
      }
      
      EditorNotificationService.show(`Loaded ${loadedFiles.length} files from workspace`, 'success');
    } catch (error) {
      console.error('Failed to load files:', error);
      EditorNotificationService.show(`Failed to load files: ${error}`, 'error');
      
      // Start with empty editor instead of demo files
      // This follows VS Code behavior where editor starts empty until files are opened
      setFiles([]);
      setActiveFileId('');
    } finally {
      setIsLoading(false);
    }
  }, [connectionStatus.connected, effectiveWorkspaceRoot]); // FIXED: Remove activeFileId dependency to prevent reloading on tab switch

  // Initialize backend connection
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Auto-load files disabled to start with empty editor
  // Files are now loaded only when explicitly requested through explorer interaction
  // useEffect(() => {
  //   console.log('Load files effect triggered:', {
  //     connected: connectionStatus.connected,
  //     propFilesLength: propFiles.length,
  //     loadFilesAvailable: !!loadFiles
  //   });
  //   
  //   if (connectionStatus.connected && propFiles.length === 0) {
  //     console.log('Triggering loadFiles...');
  //     loadFiles(); // Only auto-load if no propFiles provided
  //   }
  // }, [connectionStatus.connected, loadFiles, propFiles.length]);

  // Update files when propFiles change
  useEffect(() => {
    if (propFiles.length > 0) {
      setFiles(propFiles);
      if (propActiveFileId) {
        setActiveFileId(propActiveFileId);
      } else if (propFiles.length > 0 && !activeFileId) {
        setActiveFileId(propFiles[0].id);
      }
    }
  }, [propFiles, propActiveFileId, activeFileId]);

  // Get current active file (fresh on every render)
  const activeFile = files.find(file => file.id === activeFileId);

  // Handle content changes with auto-save (FIXED: Stable dependencies to prevent recreation)
  const handleContentChange = useCallback((newContent: string) => {
    if (!activeFileId) return;
    // Prevent edits to diff/read-only tabs
    const activeMeta = files.find(f => f.id === activeFileId) as any;
    if (activeMeta?.readOnly || activeMeta?.isDiff) {
      return; // ignore modifications
    }

    // Update the content ref immediately to prevent loops
    currentContentRef.current = newContent;

    setFiles(currentFiles => {
      const wasTemporary = currentFiles.find(f => f.id === activeFileId)?.isTemporary;
      const updatedFiles = currentFiles.map(file =>
        file.id === activeFileId
          ? { 
              ...file, 
              content: newContent, 
              modified: file.content !== newContent,
              // If this file was temporary, any edit makes it permanent
              isTemporary: wasTemporary ? false : file.isTemporary,
            }
          : file
      );

      // Auto-save logic (simplified to prevent dependency issues)
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }

      const fileToSave = updatedFiles.find(f => f.id === activeFileId);
      if (autoSaveEnabled && fileToSave?.path && fileToSave.modified) {
        autoSaveTimerRef.current = setTimeout(async () => {
          try {
            // Check connection at time of save, not when setting up the callback
            const status = await backendService.getConnectionStatus();
            if (status.connected) {
              await backendService.saveFile(fileToSave.path!, newContent);
              
              setFiles(prevFiles =>
                prevFiles.map(f =>
                  f.id === activeFileId ? { ...f, modified: false } : f
                )
              );
              
              EditorNotificationService.show(`Auto-saved ${fileToSave.name}`, 'success');
            }
          } catch (error) {
            console.error(`Failed to auto-save file ${fileToSave.name}:`, error);
            EditorNotificationService.show(`Failed to auto-save ${fileToSave.name}`, 'error');
          }
        }, autoSaveDelay);
      }
      
      return updatedFiles;
    });

    onFileChange?.(activeFileId, newContent);
  }, [activeFileId, onFileChange, autoSaveEnabled, autoSaveDelay, files]); // include files for readOnly lookup

  // Update the content change handler ref to always have the latest version
  useEffect(() => {
    contentChangeHandlerRef.current = handleContentChange;
  }, [handleContentChange]);

  // Keep a ref of the current active file id for keybindings
  useEffect(() => {
    activeFileIdRef.current = activeFileId;
  }, [activeFileId]);


  // Create editor extensions (FIXED: Stable function to prevent recreating editor)
  const createExtensions = useCallback((file: EditorFile | undefined): Extension[] => {
    const language = file?.language || 'text';
    const extensions: Extension[] = [
      lineNumbers(),
      foldGutter(),
      dropCursor(),
  // Note: Do NOT enable global line wrapping here. We'll add it conditionally
  // for .jsonl files during editor initialization to avoid layout issues in
  // other languages like Python.
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      rectangularSelection(),
      crosshairCursor(),
      highlightSelectionMatches(),
      history(),
      // Custom keybindings: Ctrl/Cmd+S to save
      keymap.of([
        {
          key: 'Mod-s',
          run: () => {
            try {
              const fn = saveHandlerRef.current;
              if (fn) fn();
            } catch (e) {
              console.warn('Save shortcut failed:', e);
            }
            // Returning true prevents the browser default Save Page dialog
            return true;
          }
        },
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        indentWithTab,
      ]),
      syntaxHighlighting(createICUISyntaxHighlighting(isDarkTheme)),
  EditorView.theme(createICUIEnhancedEditorTheme(isDarkTheme)),
      // Add update listener to handle content changes - using stable ref
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newContent = update.state.doc.toString();
          // Compare against the ref to avoid stale closure issues
          if (newContent !== currentContentRef.current) {
            currentContentRef.current = newContent;
            // Use a more stable approach by calling through ref
            if (contentChangeHandlerRef.current) {
              contentChangeHandlerRef.current(newContent);
            }
          }
        }
      }),
    ];

    // Diff highlighting (unified patch) - lightweight decoration pass
    if (language === 'diff') {
      const added = Decoration.line({ class: 'cm-diff-added' });
      const removed = Decoration.line({ class: 'cm-diff-removed' });
      const hunk = Decoration.line({ class: 'cm-diff-hunk' });
      const meta = file?.__diffMeta || { added: new Set<number>(), removed: new Set<number>(), hunk: new Set<number>() };
      const plugin = ViewPlugin.fromClass(class {
        decorations: any;
        constructor(view: EditorView) { this.decorations = this.build(view); }
        update(u: ViewUpdate) { if (u.docChanged) this.decorations = this.build(u.view); }
        build(view: EditorView) {
          const ranges: any[] = [];
          for (let i = 1; i <= view.state.doc.lines; i++) {
            if (meta.hunk.has(i)) {
              ranges.push(hunk.range(view.state.doc.line(i).from));
              continue;
            }
            if (meta.added.has(i)) {
              ranges.push(added.range(view.state.doc.line(i).from));
              continue;
            }
            if (meta.removed.has(i)) {
              ranges.push(removed.range(view.state.doc.line(i).from));
              continue;
            }
          }
          return Decoration.set(ranges);
        }
      }, { decorations: v => v.decorations });
      const diffTheme = EditorView.theme({
        '.cm-diff-added': { backgroundColor: 'rgba(76,175,80,0.18)' },
        '.cm-diff-removed': { backgroundColor: 'rgba(244,67,54,0.18)' },
        '.cm-diff-hunk': { backgroundColor: 'rgba(120,120,120,0.25)', fontStyle: 'italic' },
      });
      extensions.push(plugin, diffTheme);

      // Attempt to infer underlying language from diff header lines (--- a/path, +++ b/path)
      try {
        const underlyingPath = meta.originalPath || '';
        if (underlyingPath) {
          const ext = underlyingPath.split('.').pop()?.toLowerCase() || '';
          // Map to our language identifiers
          const underlyingLang = (
            ext === 'tsx' ? 'tsx' :
            ext === 'ts' ? 'typescript' :
            ext === 'jsx' ? 'jsx' :
            ext === 'js' ? 'javascript' :
            ext === 'py' ? 'python' :
            ext === 'md' ? 'markdown' :
            ext === 'json' || ext === 'jsonl' ? 'json' :
            ext === 'html' || ext === 'htm' ? 'html' :
            ext === 'css' || ext === 'scss' || ext === 'sass' ? 'css' :
            ext === 'yaml' || ext === 'yml' ? 'yaml' :
            ext === 'sh' || ext === 'bash' ? 'shell' :
            ext === 'cpp' || ext === 'c' || ext === 'hpp' || ext === 'h' ? 'cpp' :
            ext === 'rs' ? 'rust' :
            ext === 'go' ? 'go' :
            'text'
          );
          // Push underlying language highlighter AFTER diff decorations so token colors appear within backgrounds
          if (underlyingLang === 'typescript') {
            extensions.push(javascript({ typescript: true }));
          } else if (underlyingLang === 'tsx') {
            extensions.push(javascript({ typescript: true, jsx: true }));
          } else if (underlyingLang === 'javascript') {
            extensions.push(javascript({ jsx: false }));
          } else if (underlyingLang === 'jsx') {
            extensions.push(javascript({ jsx: true }));
          } else if (underlyingLang === 'python') {
            extensions.push(python());
          } else if (underlyingLang === 'markdown') {
            extensions.push(markdown());
          } else if (underlyingLang === 'json') {
            extensions.push(json());
          } else if (underlyingLang === 'html') {
            extensions.push(html());
          } else if (underlyingLang === 'css') {
            extensions.push(css());
          } else if (underlyingLang === 'yaml') {
            extensions.push(StreamLanguage.define(yaml));
          } else if (underlyingLang === 'shell') {
            extensions.push(StreamLanguage.define(shell));
          } else if (underlyingLang === 'cpp') {
            extensions.push(cpp());
          } else if (underlyingLang === 'rust') {
            extensions.push(rust());
          } else if (underlyingLang === 'go') {
            extensions.push(go());
          }
        }
      } catch (e) {
        console.warn('[ICUIEditor] Failed underlying language detection for diff:', e);
      }
    } else if (language === 'python') {
      extensions.push(python());
    } else if (language === 'javascript' || language === 'typescript') {
      extensions.push(javascript({ typescript: language === 'typescript' }));
    } else if (language === 'markdown') {
      extensions.push(markdown());
    } else if (language === 'json') {
      extensions.push(json());
    } else if (language === 'html') {
      extensions.push(html());
    } else if (language === 'css') {
      extensions.push(css());
    } else if (language === 'yaml') {
      extensions.push(StreamLanguage.define(yaml));
    } else if (language === 'bash' || language === 'shell' || language === 'sh') {
      extensions.push(StreamLanguage.define(shell));
    } else if (language === 'cpp' || language === 'c') {
      extensions.push(cpp());
    } else if (language === 'rust') {
      extensions.push(rust());
    } else if (language === 'go') {
      extensions.push(go());
    }
  // Note: For unsupported extensions (or diff), base theme already applied.
    // Users can manually select a language via the language selector

    return extensions;
  }, [isDarkTheme]); // Only depend on isDarkTheme

  // Initialize CodeMirror editor (FIXED: Only recreate on relevant changes)
  useEffect(() => {
    if (!editorRef.current) return;

    // Clean up existing editor
    if (editorViewRef.current) {
      editorViewRef.current.destroy();
      editorViewRef.current = null;
    }

    // Don't initialize if no active file
    if (!activeFile) {
      // No active file, skipping editor initialization
      return;
    }

    // Use activeFile content or default content for initial setup
    const initialContent = activeFile.content || '';
    
    // Initializing editor with content
    currentContentRef.current = initialContent;

    // Create new editor state
  const baseExtensions = createExtensions(activeFile);
    const isDiff = (activeFile as any).isDiff;
    if ((activeFile as any).readOnly || isDiff) {
      // Dynamically import readOnly extension only when needed to keep bundle lean
      // @ts-ignore
      baseExtensions.push(EditorState.readOnly.of(true));
    }

    // Enable soft wrap ONLY for .jsonl files
    const isJsonl = (activeFile.path || activeFile.name || '').toLowerCase().endsWith('.jsonl');
    const extensions = isJsonl ? [...baseExtensions, EditorView.lineWrapping] : baseExtensions;

    const state = EditorState.create({
      doc: initialContent,
      extensions,
    });

    // Create editor view - no custom dispatch, let CodeMirror handle it
    editorViewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    // Focus the editor
    editorViewRef.current.focus();
    // Editor initialized and focused

    return () => {
      if (editorViewRef.current) {
        editorViewRef.current.destroy();
        editorViewRef.current = null;
        // Editor instance destroyed on cleanup
      }
    };
  }, [isDarkTheme, createExtensions, activeFile?.id, activeFile?.name, activeFile?.path]); // Recreate when file identity or name/path changes

  // Update editor content when switching between files (FIXED: Prevent infinite loop)
  useEffect(() => {
    if (!editorViewRef.current || !activeFile) return;

    const currentContent = editorViewRef.current.state.doc.toString();
    
    // Editor content update check for active file
    
    // Update when content is different (file switch or content loaded)
    if (currentContent !== activeFile.content) {
      // Updating editor with new file content
      
      // Update the ref first to prevent loops
      currentContentRef.current = activeFile.content || '';
      
      // Update editor content
      editorViewRef.current.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: activeFile.content || '',
        },
      });
    }
  }, [activeFile?.id, activeFile?.content]); // Depend on both id and content

  const handleSaveFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !file.path || !connectionStatus.connected) return;

    setIsLoading(true);
    try {
      await backendService.saveFile(file.path, file.content);
      
      // Mark file as saved
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === fileId 
            ? { ...f, modified: false }
            : f
        )
      );
      
      EditorNotificationService.show(`Saved ${file.name}`, 'success');
      onFileSave?.(fileId);
    } catch (error) {
      console.error('Failed to save file:', error);
      EditorNotificationService.show(`Failed to save ${file.name}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files, connectionStatus.connected, onFileSave]);

  // Expose save handler via a ref so keymap can call latest function without recreating extensions
  useEffect(() => {
    saveHandlerRef.current = () => {
      const id = activeFileIdRef.current;
      if (id) {
        return handleSaveFile(id);
      }
    };
  }, [handleSaveFile]);

  const handleRunFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !connectionStatus.connected) return;

    setIsLoading(true);
    try {
      const result = await backendService.executeCode(file.content, file.language, file.path);
      EditorNotificationService.show(`Executed ${file.name}`, 'success');
      onFileRun?.(fileId, file.content, file.language);
    } catch (error) {
      console.error('Failed to execute file:', error);
      EditorNotificationService.show(`Failed to execute ${file.name}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files, connectionStatus.connected, onFileRun]);

  const handleCloseFile = useCallback((fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;

    // Save current editor content before closing if this is the active file
    if (fileId === activeFileId && editorViewRef.current) {
      const currentContent = editorViewRef.current.state.doc.toString();
      if (currentContent !== file.content) {
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === fileId 
              ? { ...f, content: currentContent, modified: f.content !== currentContent }
              : f
          )
        );
        // Update the file object for the confirmation dialog
        Object.assign(file, { content: currentContent, modified: file.content !== currentContent });
      }
    }

    if (file.modified) {
      // Use global confirm dialog
      // Lazy import to avoid cyc dependency in large file
      const { confirmService } = require('../../services/confirmService');
      const shouldSave = (confirmService as typeof import('../../services/confirmService').confirmService)
        .confirm({ title: 'Unsaved Changes', message: `${file.name} has unsaved changes. Save before closing?`, confirmText: 'Save', cancelText: 'Discard' });
      // Note: confirm() returns Promise<boolean>, handle in then to keep function sync
      (async () => {
        const ok = await shouldSave;
        if (ok && connectionStatus.connected && file.path) {
          handleSaveFile(fileId);
        }
        // Proceed to close regardless after handling save choice
        setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
        if (fileId === activeFileId) {
          const remainingFiles = files.filter(f => f.id !== fileId);
          if (remainingFiles.length > 0) {
            setActiveFileId(remainingFiles[0].id);
          } else {
            setActiveFileId('');
          }
        }
        onFileClose?.(fileId);
      })();
      return; // Defer further logic to async block
    }
    // If not modified, proceed to close immediately
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
    if (fileId === activeFileId) {
      const remainingFiles = files.filter(f => f.id !== fileId);
      setActiveFileId(remainingFiles[0]?.id || '');
    }
    onFileClose?.(fileId);
  }, [files, activeFileId, connectionStatus.connected, onFileClose, handleSaveFile]);

  const handleActivateFile = useCallback(async (fileId: string) => {
    console.log('Activating file:', fileId);
    
    // Save current editor content before switching
    if (activeFileId && editorViewRef.current) {
      const currentContent = editorViewRef.current.state.doc.toString();
      const currentFile = files.find(f => f.id === activeFileId);
      
      if (currentFile && currentContent !== currentFile.content) {
        // console.log('Saving current file content before switch');
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === activeFileId 
              ? { ...f, content: currentContent, modified: currentFile.content !== currentContent }
              : f
          )
        );
      }
    }
    
    // If clicking on a temporary file tab, make it permanent (VS Code behavior)
    const targetFile = files.find(f => f.id === fileId);
    if (targetFile?.isTemporary) {
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, isTemporary: false } : f
      ));
      EditorNotificationService.show(`${targetFile.name} is now permanent`, 'info');
    }
    
    // Load file content if it's not already loaded BEFORE setting as active
    const file = files.find(f => f.id === fileId);
    // console.log('Found file for activation:', file);
    
    if (file && file.path && connectionStatus.connected) {
      // Load content if it's empty or not loaded yet
      const needsContent = !file.content || file.content.trim() === '';
      
      console.log('File needs content?', needsContent, 'Current content length:', file.content?.length || 0);
      
      if (needsContent) {
        try {
          console.log('Loading content for file:', file.path);
          const fileWithContent = await backendService.getFile(file.path);
          console.log('Loaded content, length:', fileWithContent.content.length);
          
          // Update the file content first
          setFiles(prevFiles => 
            prevFiles.map(f => 
              f.id === fileId 
                ? { ...f, content: fileWithContent.content }
                : f
            )
          );
          
          // Wait a tick to ensure state is updated before setting active file
          await new Promise(resolve => setTimeout(resolve, 0));
        } catch (error) {
          console.warn(`Failed to load content for ${file.name}:`, error);
          EditorNotificationService.show(`Failed to load ${file.name}`, 'warning');
        }
      }
    }
    
    // Set active file after content is loaded
    setActiveFileId(fileId);
    onFileActivate?.(fileId);
  }, [files, activeFileId, connectionStatus.connected, onFileActivate]);

  // Cleanup auto-save timer on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, []);

  return (
  <div className={`icui-editor-container h-full flex flex-col ${className}`}>
      {/* File Tabs - FIXED: Use ICUI theme variables for consistency */}
  <div className="flex border-b icui-tabs">
        {files.map((file) => (
          <div
            key={file.id}
    className={`icui-tab ${file.id === activeFileId ? 'active' : ''}`}
            onClick={() => handleActivateFile(file.id)}
          >
            <span className={`icui-tab-title ${file.isTemporary ? 'italic' : ''}`}>
              {file.name}
              {file.modified && <span className="ml-1 icui-dot-modified">•</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCloseFile(file.id);
              }}
      className="icui-close-btn"
            >
              ×
            </button>
          </div>
        ))}

      </div>

      {/* File Actions - Simplified without connection status */}
      {activeFile && (
        <div className="flex items-center justify-between p-2 border-b icui-editor-actions">
          <div className="flex items-center space-x-4">
            <span className="text-xs font-mono icui-text-secondary">
              {activeFile.path || `${effectiveWorkspaceRoot}/${activeFile.name}`}
            </span>
            {isLoading && (
              <div className="icui-spinner" />
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleSaveFile(activeFile.id)}
              disabled={!activeFile.modified || !connectionStatus.connected || isLoading}
              className="px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed icui-btn-save"
            >
              Save
            </button>
            <div className="flex items-center space-x-1">
              <input
                type="checkbox"
                id="auto-save-checkbox"
                checked={autoSaveEnabled}
                onChange={(e) => {
                  setAutoSaveEnabled(e.target.checked);
                  if (e.target.checked) {
                    EditorNotificationService.show('Auto-save enabled', 'info');
                  } else {
                    EditorNotificationService.show('Auto-save disabled', 'info');
                  }
                }}
                className="w-3 h-3"
              />
              <label htmlFor="auto-save-checkbox" className="text-xs cursor-pointer icui-text-secondary">
                Auto
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Editor Container */}
      <div className="flex-1 relative overflow-hidden">
        {activeFile && files.find(f => f.id === activeFileId) ? (
          <div ref={editorRef} className="h-full w-full" />
        ) : (
    <div className="flex items-center justify-center h-full icui-editor-empty">
            <div className="text-center">
              <p className="text-lg mb-2">No file open</p>
              {onFileCreate && (
                <button
                  onClick={onFileCreate}
      className="px-4 py-2 rounded transition-colors icui-btn-accent"
                >
                  Create New File
                </button>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Language Fallback Selector Modal */}
      {showLanguageFallback && pendingFile && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => {
            setShowLanguageFallback(false);
            setPendingFile(null);
          }}
        >
          <div className="icui-modal rounded-lg shadow-lg p-6 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-4">Select Language Highlighting</h3>
            <p className="text-sm mb-4 icui-text-secondary">
              The file extension for "{pendingFile.file.name}" is not recognized. Please select a syntax highlighting mode:
            </p>
            <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto">
              {supportedLanguages.map((lang) => (
                <button
                  key={lang.id}
                  onClick={() => handleLanguageFallback(lang.id)}
                  className="icui-language-button text-sm"
                >
                  {lang.name}
                </button>
              ))}
            </div>
            <div className="flex justify-end mt-4 space-x-2">
              <button
                onClick={() => {
                  setShowLanguageFallback(false);
                  setPendingFile(null);
                }}
                className="icui-button-secondary text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

// Set display name for debugging
ICUIEditor.displayName = 'ICUIEditor';

export default ICUIEditor;
export type { ICUIEditorRef };
