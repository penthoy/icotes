/**
 * ICUI Editor Component
 * 
 * Updated to use centralized backend service and workspace utilities.
 * This eliminates code duplication and provides consistent behavior.
 * 
 * Key Features:
 * - Centralized backend service for file operations
 * - Auto-save with debouncing
 * - Real-time file loading from backend
 * - CodeMirror 6 integration with syntax highlighting
 * - Theme detection and workspace root integration
 * - Error handling and connection status display
 */

import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { EditorView } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { backendService, useTheme, ConnectionStatus } from '../../services';
import { getWorkspaceRoot } from '../../lib';

// Import from editor module
import { 
  EditorFile, 
  ICUIEditorRef, 
  EditorNotificationService,
  ImageViewerPanel,
  EditorTabBar,
  EditorActionBar,
  LanguageSelectorModal,
  detectLanguageFromExtension,
  supportedLanguages,
  processDiffPatch,
  createEditorExtensions,
  useFileOperations
} from '../editor';

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
      
      // Auto-detect language from file extension first
      const detectedLanguage = detectLanguageFromExtension(filePath);
      
      // For image files, we don't need to load the text content
      if (detectedLanguage === 'image') {
        const fileName = filePath.split('/').pop() || 'image';
        
        // Check if this image is already open
        const existingFileIndex = files.findIndex(f => f.path === filePath && !(f as any).isDiff);
        if (existingFileIndex >= 0) {
          // File is already open - force refresh by creating a new file ID
          // This ensures React re-renders the ImageViewerPanel with fresh state
          const fileData = {
            id: `file-${Date.now()}-${Math.random()}`, // New ID to force refresh
            name: fileName,
            path: filePath,
            content: '', // No content needed for images
            language: 'image',
            modified: false,
            isTemporary: false
          };
          
          // Replace the existing file with the new one to force refresh
          setFiles(prev => prev.map((f, index) => 
            index === existingFileIndex ? fileData : f
          ));
          setActiveFileId(fileData.id);
        } else {
          // Add new image file
          const fileData = {
            id: `file-${Date.now()}-${Math.random()}`,
            name: fileName,
            path: filePath,
            content: '', // No content needed for images
            language: 'image',
            modified: false,
            isTemporary: false
          };
          setFiles(prev => [...prev, fileData]);
          setActiveFileId(fileData.id);
        }
        
        EditorNotificationService.show(`Opened ${fileName}`, 'success');
        setIsLoading(false);
        return;
      }
      
      // For non-image files, load the content
      const fileData = await backendService.getFile(filePath);
      
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
        // File is already open - reload content from disk to ensure it's fresh
        // This fixes the issue where clicking on a file doesn't show updated content
        setFiles(prev => prev.map((f, index) => 
          index === existingFileIndex ? { 
            ...f, 
            content: fileWithLanguage.content,
            isTemporary: false, 
            language: detectedLanguage,
            modified: false // Reset modified flag since we're loading fresh content
          } : f
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
      
      // Auto-detect language from file extension first
      const detectedLanguage = detectLanguageFromExtension(filePath);
      
      // Check if file is already open
      const existingFileIndex = files.findIndex(f => f.path === filePath);
      if (existingFileIndex >= 0) {
        // File is already open, just activate it
        const existingFile = files[existingFileIndex];
        setActiveFileId(existingFile.id);
        setIsLoading(false);
        return;
      }

      // VS Code behavior: Only replace existing temporary files, not permanent ones
      const temporaryFiles = files.filter(f => f.isTemporary);
      if (temporaryFiles.length > 0) {
        // Remove all temporary files since we're opening a new temporary file
        setFiles(prev => prev.filter(f => !f.isTemporary));
      }

      // For image files, we don't need to load the text content
      if (detectedLanguage === 'image') {
        const fileName = filePath.split('/').pop() || 'image';
        const fileData = {
          id: `file-${Date.now()}-${Math.random()}`,
          name: fileName,
          path: filePath,
          content: '', // No content needed for images
          language: 'image',
          modified: false,
          isTemporary: true
        };
        
        setFiles(prev => [...prev.filter(f => !f.isTemporary), fileData]);
        setActiveFileId(fileData.id);
        EditorNotificationService.show(`Opened ${fileName} (temporary)`, 'info');
        setIsLoading(false);
        return;
      }

      // Load the new file and mark it as temporary
      const fileData = await backendService.getFile(filePath);
      
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
  }, [files, detectLanguageFromExtension]);

  const openFilePermanent = useCallback(async (filePath: string) => {
    await openFile(filePath);
  }, [openFile]);

  // Open synthetic diff (for untracked files)
  const openSyntheticDiff = useCallback(async (filePath: string, patch: string) => {
    console.log('[ICUIEditor] openSyntheticDiff called for:', filePath);
    try {
      setIsLoading(true);
      const tabId = `diff:${filePath}`;
      
      // Check if tab already exists
      const existing = files.find(f => f.id === tabId);
      if (existing) {
        console.log('[ICUIEditor] Synthetic diff tab already exists, focusing:', tabId);
        setActiveFileId(tabId);
        return;
      }
      
      // Process diff using extracted utility
      const processed = processDiffPatch(patch);
      const name = `${filePath.split('/').pop() || filePath} (diff)`;
      
      // Detect language from file extension for syntax highlighting
      const detectedLang = detectLanguageFromExtension(filePath);
      const language = detectedLang || 'text';
      console.log('[ICUIEditor] Detected language for synthetic diff:', language);
      
      const diffFile: EditorFile = {
        id: tabId,
        name,
        language, // Use actual file language for syntax highlighting
        content: processed.content,
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
        __diffMeta: { ...processed.metadata, originalPath: filePath }
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
      const tabId = `diff:${filePath}`;
      
      // Check if tab already exists
      const existing = files.find(f => f.id === tabId);
      if (existing) {
        console.log('[ICUIEditor] Diff tab already exists, focusing:', tabId);
        setActiveFileId(tabId);
        return;
      }
      
      // Fetch diff from backend
      console.log('[ICUIEditor] Fetching diff from backend...');
      const diffData = await backendService.getScmDiff(filePath);
      console.log('[ICUIEditor] Diff data received:', diffData);
      
      if (!diffData || typeof diffData.patch !== 'string') {
        console.warn('[ICUIEditor] No valid diff data:', diffData);
        EditorNotificationService.show(`No diff available for ${filePath}`, 'warning');
        return;
      }
      
      // Process diff using extracted utility
      const name = `${filePath.split('/').pop() || filePath} (diff)`;
      console.log('[ICUIEditor] Creating new diff tab:', name);
      const processed = processDiffPatch(diffData.patch);
      
      // Detect language from file extension for syntax highlighting
      const detectedLang = detectLanguageFromExtension(filePath);
      const language = detectedLang || 'text';
      console.log('[ICUIEditor] Detected language for diff:', language);
      
      const diffFile: EditorFile = {
        id: tabId,
        name,
        language, // Use actual file language for syntax highlighting
        content: processed.content,
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
        __diffMeta: { ...processed.metadata, originalPath: filePath }
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

  // Initialize backend connection with faster initial check
  useEffect(() => {
    // Initial connection check
    checkBackendConnection().catch(error => {
      console.warn('[ICUIEditor] Initial connection check failed:', error);
    });
    
    // Check more frequently initially, then less frequently
    const quickInterval = setInterval(checkBackendConnection, 2000); // Check every 2s initially
    let slowInterval: ReturnType<typeof setInterval> | null = null;
    const slowTimeout = setTimeout(() => {
      clearInterval(quickInterval);
      slowInterval = setInterval(checkBackendConnection, 30000); // Then every 30s
    }, 10000); // Switch to slow interval after 10s
    
    return () => {
      clearInterval(quickInterval);
      clearTimeout(slowTimeout);
      if (slowInterval) {
        clearInterval(slowInterval);
      }
    };
  }, [checkBackendConnection]);

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
  }, [activeFileId, onFileChange, autoSaveEnabled, autoSaveDelay]); // files dependency removed for performance

  // Update the content change handler ref to always have the latest version
  useEffect(() => {
    contentChangeHandlerRef.current = handleContentChange;
  }, [handleContentChange]);

  // Keep a ref of the current active file id for keybindings
  useEffect(() => {
    activeFileIdRef.current = activeFileId;
  }, [activeFileId]);


  // Create editor extensions using extracted factory
  const extensions = React.useMemo(() => {
    return createEditorExtensions({
      file: activeFile,
      isDarkTheme,
      saveHandlerRef,
      contentChangeHandlerRef,
      currentContentRef
    });
  }, [activeFile?.id, activeFile?.language, isDarkTheme]);

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
    const baseExtensions = extensions;
    const isDiff = (activeFile as any).isDiff;
    if ((activeFile as any).readOnly || isDiff) {
      // Dynamically import readOnly extension only when needed to keep bundle lean
      // @ts-ignore
      baseExtensions.push(EditorState.readOnly.of(true));
    }

    // Enable soft wrap ONLY for .jsonl files
    const isJsonl = (activeFile.path || activeFile.name || '').toLowerCase().endsWith('.jsonl');
    const finalExtensions = isJsonl ? [...baseExtensions, EditorView.lineWrapping] : baseExtensions;

    const state = EditorState.create({
      doc: initialContent,
      extensions: finalExtensions,
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
  }, [isDarkTheme, extensions, activeFile?.id, activeFile?.name, activeFile?.path]); // Recreate when file identity or name/path changes

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
      {/* File Tabs */}
      <EditorTabBar
        files={files}
        activeFileId={activeFileId}
        onActivateFile={handleActivateFile}
        onCloseFile={handleCloseFile}
      />

      {/* File Actions */}
      {activeFile && (
        <EditorActionBar
          activeFile={activeFile}
          isLoading={isLoading}
          connectionStatus={connectionStatus}
          autoSaveEnabled={autoSaveEnabled}
          effectiveWorkspaceRoot={effectiveWorkspaceRoot}
          onSave={() => handleSaveFile(activeFile.id)}
          onToggleAutoSave={(enabled) => {
            setAutoSaveEnabled(enabled);
            EditorNotificationService.show(
              `Auto-save ${enabled ? 'enabled' : 'disabled'}`,
              'info'
            );
          }}
        />
      )}

      {/* Editor Container */}
      <div className="flex-1 relative overflow-hidden">
        {activeFile && files.find(f => f.id === activeFileId) ? (
          activeFile.language === 'image' ? (
            // Image Viewer - Display images like VS Code with enhanced features
            // Key prop ensures React creates a new instance for each different image file
            <ImageViewerPanel 
              key={activeFile.path || activeFile.id}
              filePath={activeFile.path || ''}
              fileName={activeFile.name}
            />
          ) : (
            // Code Editor
            <div ref={editorRef} className="h-full w-full" />
          )
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
        <LanguageSelectorModal
          fileName={pendingFile.file.name}
          onSelect={handleLanguageFallback}
          onCancel={() => {
            setShowLanguageFallback(false);
            setPendingFile(null);
          }}
        />
      )}
    </div>
  );
});

// Set display name for debugging
ICUIEditor.displayName = 'ICUIEditor';

export default ICUIEditor;
export type { ICUIEditorRef };
