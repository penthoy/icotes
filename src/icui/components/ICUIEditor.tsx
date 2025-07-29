/**
 * ICUI Editor Component
 * 
 * Updated to use centralized backend service and workspace utilities.
 * This eliminates code duplication and provides consistent behavior.
 * 
 * Key Features:
 * - Centralized backend service for file operations
 * - Multi-file tabs with backend synchronization
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
} from "@codemirror/view";
import { EditorState, Extension } from "@codemirror/state";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { backendService, ICUIFile, useTheme, ConnectionStatus } from '../services';
import { getWorkspaceRoot } from '../lib';
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
import { createICUISyntaxHighlighting, createICUIEnhancedEditorTheme } from '../utils/syntaxHighlighting';

// File interface (using centralized ICUIFile type)
interface EditorFile extends ICUIFile {
  isTemporary?: boolean; // VS Code-like temporary file state
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
  autoSave = true,
  autoSaveDelay = 1500,
  workspaceRoot
}, ref) => {
  // State management (following simpleeditor pattern)
  const [files, setFiles] = useState<EditorFile[]>(propFiles);
  const [activeFileId, setActiveFileId] = useState<string>(propActiveFileId || '');
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Refs (following ICUIEnhancedEditorPanel pattern)
  const editorRef = useRef<HTMLDivElement>(null);
  const editorViewRef = useRef<EditorView | null>(null);
  // Use centralized theme service instead of manual theme detection
  const { theme } = useTheme();
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentContentRef = useRef<string>(''); // Track current content to prevent loops
  const contentChangeHandlerRef = useRef<((content: string) => void) | null>(null); // Stable ref for content changes

  // Get workspace root from environment (following ICUIExplorer pattern)
  const effectiveWorkspaceRoot = workspaceRoot || getWorkspaceRoot();

  // File opening methods for external control (e.g., from Explorer)
  const openFile = useCallback(async (filePath: string) => {
    try {
      setIsLoading(true);
      const fileData = await backendService.getFile(filePath);
      
      // Check if file is already open
      const existingFileIndex = files.findIndex(f => f.path === filePath);
      if (existingFileIndex >= 0) {
        // File is already open, just activate it and mark as permanent
        setFiles(prev => prev.map((f, index) => 
          index === existingFileIndex ? { ...f, isTemporary: false } : f
        ));
        setActiveFileId(files[existingFileIndex].id);
      } else {
        // Add new file to the list as permanent
        const permanentFile = { ...fileData, isTemporary: false };
        setFiles(prev => [...prev, permanentFile]);
        setActiveFileId(permanentFile.id);
      }
      
      EditorNotificationService.show(`Opened ${fileData.name}`, 'success');
    } catch (error) {
      console.error('Failed to open file:', error);
      EditorNotificationService.show(`Failed to open ${filePath}: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files]);

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
      const temporaryFile = { ...fileData, isTemporary: true };
      
      // Add new temporary file to the list (keeping all permanent files)
      setFiles(prev => [...prev.filter(f => !f.isTemporary), temporaryFile]);
      setActiveFileId(temporaryFile.id);
      
      EditorNotificationService.show(`Opened ${fileData.name} (temporary)`, 'info');
    } catch (error) {
      console.error('Failed to open temporary file:', error);
      EditorNotificationService.show(`Failed to open ${filePath}: ${error}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [files]);

  const openFilePermanent = useCallback(async (filePath: string) => {
    // For permanent files, same as openFile for now
    // This will be enhanced in the next phases for proper VS Code behavior
    await openFile(filePath);
  }, [openFile]);

  // Expose methods via ref for external control
  useImperativeHandle(ref, () => ({
    openFile,
    openFileTemporary, 
    openFilePermanent
  }), [openFile, openFileTemporary, openFilePermanent]);

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
      console.log('Backend connection status updated:', newStatus);
      console.log('onConnectionStatusChange callback exists:', !!onConnectionStatusChange);
      setConnectionStatus(newStatus);
      if (onConnectionStatusChange) {
        console.log('Calling onConnectionStatusChange callback with:', newStatus);
        onConnectionStatusChange(newStatus);
      } else {
        console.log('No onConnectionStatusChange callback available');
      }
      return status.connected;
    } catch (error) {
      const newStatus = {
        connected: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      };
      console.log('Backend connection error:', newStatus);
      console.log('onConnectionStatusChange callback exists:', !!onConnectionStatusChange);
      setConnectionStatus(newStatus);
      if (onConnectionStatusChange) {
        console.log('Calling onConnectionStatusChange callback with error:', newStatus);
        onConnectionStatusChange(newStatus);
      } else {
        console.log('No onConnectionStatusChange callback available');
      }
      return false;
    }
  }, []); // Remove onConnectionStatusChange from dependencies to prevent infinite loops

  // Load files from workspace (following simpleeditor pattern)
  const loadFiles = useCallback(async () => {
    if (!connectionStatus.connected) return;
    
    setIsLoading(true);
    try {
      console.log('Loading files from workspace:', effectiveWorkspaceRoot);
      // First, get the list of files without content
      const loadedFiles = await backendService.getWorkspaceFiles(effectiveWorkspaceRoot);
      console.log('Loaded file list:', loadedFiles);
      
      if (loadedFiles.length > 0) {
        // Load content for the first file immediately before setting files
        try {
          console.log('Loading content for first file:', loadedFiles[0].path);
          const fileWithContent = await backendService.getFile(loadedFiles[0].path!);
          console.log('Loaded content for first file, length:', fileWithContent.content.length);
          
          // Update the first file with content
          loadedFiles[0] = { ...loadedFiles[0], content: fileWithContent.content };
        } catch (error) {
          console.warn(`Failed to load content for ${loadedFiles[0].name}:`, error);
        }
        
        // Set files list with first file content loaded
        setFiles(loadedFiles);
        
        // Set the first file as active if no active file is set
        if (!activeFileId) {
          console.log('Setting active file to:', loadedFiles[0].id);
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

    // Update the content ref immediately to prevent loops
    currentContentRef.current = newContent;

    setFiles(currentFiles => {
      const updatedFiles = currentFiles.map(file =>
        file.id === activeFileId
          ? { ...file, content: newContent, modified: file.content !== newContent }
          : file
      );

      // Auto-save logic (simplified to prevent dependency issues)
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }

      const fileToSave = updatedFiles.find(f => f.id === activeFileId);
      if (autoSave && fileToSave?.path && fileToSave.modified) {
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
  }, [activeFileId, onFileChange, autoSave, autoSaveDelay]); // FIXED: Removed connectionStatus.connected dependency

  // Update the content change handler ref to always have the latest version
  useEffect(() => {
    contentChangeHandlerRef.current = handleContentChange;
  }, [handleContentChange]);

  // Create editor extensions (FIXED: Stable function to prevent recreating editor)
  const createExtensions = useCallback((language: string): Extension[] => {
    const extensions: Extension[] = [
      lineNumbers(),
      dropCursor(),
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      autocompletion(),
      rectangularSelection(),
      crosshairCursor(),
      highlightSelectionMatches(),
      history(),
      keymap.of([
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
      EditorView.theme({
        '&': {
          height: '100%',
        },
        '.cm-scroller': {
          fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          fontSize: '14px',
          overflow: 'auto',
          height: '100%',
        },
        '.cm-editor': {
          height: '100%',
        },
        '.cm-content': {
          padding: '10px',
          minHeight: 'calc(100% - 20px)', // Account for padding
        },
        '.cm-focused': {
          outline: 'none',
        },
      }),
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

    // Add language-specific extension directly based on language
    if (language === 'python') {
      extensions.push(python());
    } else if (language === 'javascript' || language === 'typescript') {
      extensions.push(javascript());
    }
    // Add more languages as needed

    return extensions;
  }, [isDarkTheme]); // Only depend on isDarkTheme, not handleContentChange

  // Initialize CodeMirror editor (FIXED: Only recreate on theme change, not file change)
  useEffect(() => {
    if (!editorRef.current) return;

    // Clean up existing editor
    if (editorViewRef.current) {
      editorViewRef.current.destroy();
      editorViewRef.current = null;
    }

    // Don't initialize if no active file
    if (!activeFile) {
      console.log('No active file, skipping editor initialization');
      return;
    }

    // Use activeFile content or default content for initial setup
    const initialContent = activeFile.content || '';
    
    console.log('Initializing editor with content:', initialContent.substring(0, 100) + (initialContent.length > 100 ? '...' : ''));
    currentContentRef.current = initialContent;

    // Create new editor state
    const state = EditorState.create({
      doc: initialContent,
      extensions: createExtensions(activeFile.language || 'javascript'),
    });

    // Create editor view - no custom dispatch, let CodeMirror handle it
    editorViewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    // Focus the editor
    editorViewRef.current.focus();
    console.log('Editor initialized and focused');

    return () => {
      if (editorViewRef.current) {
        editorViewRef.current.destroy();
        editorViewRef.current = null;
        console.log('Editor instance destroyed on cleanup');
      }
    };
  }, [isDarkTheme, createExtensions, activeFile?.id]); // FIXED: Removed activeFile.content dependency

  // Update editor content when switching between files (FIXED: Prevent infinite loop)
  useEffect(() => {
    if (!editorViewRef.current || !activeFile) return;

    const currentContent = editorViewRef.current.state.doc.toString();
    
    console.log('Editor content update check:');
    console.log('- Active file:', activeFile.id);
    console.log('- Current editor content length:', currentContent.length);
    console.log('- Active file content length:', activeFile.content?.length || 0);
    console.log('- Content matches?', currentContent === activeFile.content);
    
    // Update when content is different (file switch or content loaded)
    if (currentContent !== activeFile.content) {
      console.log('Updating editor with new file content');
      
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
      // In a real implementation, you'd show a confirmation dialog
      const shouldSave = window.confirm(`${file.name} has unsaved changes. Save before closing?`);
      if (shouldSave && connectionStatus.connected && file.path) {
        handleSaveFile(fileId);
      }
    }

    // Remove the file from the files array
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
    
    // If closing active file, switch to another file
    if (fileId === activeFileId) {
      const remainingFiles = files.filter(f => f.id !== fileId);
      if (remainingFiles.length > 0) {
        setActiveFileId(remainingFiles[0].id);
      } else {
        // No files left, clear the active file
        setActiveFileId('');
      }
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
        console.log('Saving current file content before switch');
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
    console.log('Found file for activation:', file);
    
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
      <div className="flex border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
        {files.map((file) => (
          <div
            key={file.id}
            className={`flex items-center px-3 py-2 border-r cursor-pointer min-w-0 transition-all duration-200 ${
              file.id === activeFileId
                ? 'border-b-2'
                : ''
            }`}
            style={{
              backgroundColor: file.id === activeFileId 
                ? 'var(--icui-bg-tertiary)' 
                : 'transparent',
              borderRightColor: 'var(--icui-border-subtle)',
              borderBottomColor: file.id === activeFileId ? 'var(--icui-accent)' : 'transparent',
              color: file.id === activeFileId ? 'var(--icui-text-primary)' : 'var(--icui-text-secondary)'
            }}
            onClick={() => handleActivateFile(file.id)}
            onMouseEnter={(e) => {
              if (file.id !== activeFileId) {
                e.currentTarget.style.backgroundColor = 'var(--icui-bg-tertiary)';
              }
            }}
            onMouseLeave={(e) => {
              if (file.id !== activeFileId) {
                e.currentTarget.style.backgroundColor = 'transparent';
              }
            }}
          >
            <span className="truncate text-sm" style={{ fontStyle: file.isTemporary ? 'italic' : 'normal' }}>
              {file.name}
              {file.modified && <span style={{ color: 'var(--icui-warning)' }} className="ml-1">•</span>}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCloseFile(file.id);
              }}
              className="ml-2 text-xs transition-colors hover:opacity-80"
              style={{ color: 'var(--icui-text-secondary)' }}
            >
              ×
            </button>
          </div>
        ))}
        <button
          onClick={onFileCreate}
          className="px-3 py-2 text-sm transition-colors hover:opacity-80"
          style={{ color: 'var(--icui-text-secondary)' }}
          title="New File"
        >
          +
        </button>
      </div>

      {/* File Actions - Simplified without connection status */}
      {activeFile && (
        <div className="flex items-center justify-between p-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
          <div className="flex items-center space-x-4">
            <span className="text-xs font-mono" style={{ color: 'var(--icui-text-secondary)' }}>
              {activeFile.path || `${effectiveWorkspaceRoot}/${activeFile.name}`}
            </span>
            {isLoading && (
              <div 
                className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" 
                style={{ borderColor: 'var(--icui-accent)', borderTopColor: 'transparent' }}
              />
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => handleSaveFile(activeFile.id)}
              disabled={!activeFile.modified || !connectionStatus.connected || isLoading}
              className="px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ 
                backgroundColor: 'var(--icui-success)', 
                color: 'white',
                opacity: (!activeFile.modified || !connectionStatus.connected || isLoading) ? 0.5 : 1
              }}
            >
              Save
            </button>
            <button
              onClick={() => handleRunFile(activeFile.id)}
              disabled={!connectionStatus.connected || isLoading}
              className="px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ 
                backgroundColor: 'var(--icui-accent)', 
                color: 'white',
                opacity: (!connectionStatus.connected || isLoading) ? 0.5 : 1
              }}
            >
              Run
            </button>
          </div>
        </div>
      )}

      {/* Editor Container */}
      <div className="flex-1 relative overflow-hidden">
        {activeFile && files.find(f => f.id === activeFileId) ? (
          <div 
            ref={editorRef} 
            className="h-full w-full"
            style={{ height: '100%' }}
          />
        ) : (
          <div className="flex items-center justify-center h-full" style={{ color: 'var(--icui-text-secondary)' }}>
            <div className="text-center">
              <p className="text-lg mb-2">No file open</p>
              {onFileCreate && (
                <button
                  onClick={onFileCreate}
                  className="px-4 py-2 rounded transition-colors"
                  style={{ backgroundColor: 'var(--icui-accent)', color: 'white' }}
                >
                  Create New File
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

// Set display name for debugging
ICUIEditor.displayName = 'ICUIEditor';

export default ICUIEditor;
export type { ICUIEditorRef };
