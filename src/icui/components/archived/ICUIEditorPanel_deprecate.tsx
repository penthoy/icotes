/**
 * ICUI Enhanced Editor Panel - Combined Implementation
 * Combines the best features from multiple implementations:
 * - Excellent syntax highlighting and editor features
 * - Tabs functionality for multiple files
 * - Full ICUI framework integration
 * - Clean, minimal architecture
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
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
import { createICUISyntaxHighlighting, createICUIEnhancedEditorTheme, getLanguageExtension } from '../../utils/syntaxHighlighting';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';

// Re-export interface for compatibility
export interface ICUIEditorFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
}

export interface ICUIEditorPanelProps {
  className?: string;
  files?: ICUIEditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, newContent: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileReorder?: (fromIndex: number, toIndex: number) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
  enableDragDrop?: boolean;
}

const ICUIEditorPanel: React.FC<ICUIEditorPanelProps> = ({
  className = '',
  files = [],
  activeFileId,
  onFileChange,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  onFileActivate,
  onFileReorder,
  autoSave = false,
  autoSaveDelay = 1000,
  enableDragDrop = false,
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
  const [draggedFile, setDraggedFile] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  // Auto-save timer
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Get current active file
  const activeFile = files.find(f => f.id === activeFileId) || files[0];

  // Default file if no files provided
  const defaultFile: ICUIEditorFile = {
    id: 'default',
    name: 'main.py',
    language: 'python',
    content: `# ICUI Enhanced Editor with Tabs!
# Combining the best features from multiple implementations

def enhanced_example():
    """Enhanced editor with excellent syntax highlighting and tabs"""
    print("Welcome to ICUI Enhanced Editor!")
    return "Framework abstraction complete!"

# Test the enhanced functionality
if __name__ == "__main__":
    result = enhanced_example()
    print(f"Result: {result}")
    
    # More Python features
    numbers = [1, 2, 3, 4, 5]
    squares = [x**2 for x in numbers if x % 2 == 0]
    print(f"Even squares: {squares}")
    
    # Class example
    class CodeEditor:
        def __init__(self, name):
            self.name = name
            self.files = []
        
        def add_file(self, filename):
            self.files.append(filename)
            return f"Added {filename} to {self.name}"
    
    editor = CodeEditor("ICUI Enhanced")
    print(editor.add_file("example.py"))`,
    modified: false,
  };

  const currentFile = activeFile || defaultFile;

  // Detect theme changes
  useEffect(() => {
    const detectTheme = () => {
      const htmlElement = document.documentElement;
      const isDark = htmlElement.classList.contains('dark') || 
                     htmlElement.classList.contains('icui-theme-github-dark') ||
                     htmlElement.classList.contains('icui-theme-monokai') ||
                     htmlElement.classList.contains('icui-theme-one-dark');

      setIsDarkTheme(isDark);
    };

    detectTheme();
    
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Initialize CodeMirror editor (only recreate on theme changes)
  useEffect(() => {
    if (!editorRef.current) return;

    // Get current content from existing view if it exists, otherwise use current file content
    const currentContent = viewRef.current?.state.doc.toString() || currentFile.content;

    // Clean up existing view
    if (viewRef.current) {
      viewRef.current.destroy();
      viewRef.current = null;
    }

    // Create enhanced theme for CodeMirror using abstracted function
    const enhancedTheme = EditorView.theme(createICUIEnhancedEditorTheme(isDarkTheme));

    // Create extensions array with proper ordering
    const extensions: Extension[] = [
      lineNumbers(),
      foldGutter(),
      dropCursor(),
      EditorState.allowMultipleSelections.of(true),
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
      enhancedTheme,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const newContent = update.state.doc.toString();
          if (newContent !== currentFile.content) {
            onFileChange?.(currentFile.id, newContent);
            
            // Auto-save functionality
            if (autoSave) {
              if (autoSaveTimerRef.current) {
                clearTimeout(autoSaveTimerRef.current);
              }
              autoSaveTimerRef.current = setTimeout(() => {
                onFileSave?.(currentFile.id);
              }, autoSaveDelay);
            }
          }
        }
      }),
    ];

    // Add language extension directly based on current file language
    if (currentFile.language === 'python') {
      extensions.push(python());
    } else if (currentFile.language === 'javascript') {
      extensions.push(javascript());
    } else if (currentFile.language === 'typescript') {
      extensions.push(javascript({ typescript: true }));
    }

    // Create new editor state
    const state = EditorState.create({
      doc: currentContent,
      extensions,
    });

    // Create new editor view
    viewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    return () => {
      if (viewRef.current) {
        viewRef.current.destroy();
        viewRef.current = null;
      }
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [isDarkTheme, currentFile.language]); // Only recreate when theme or language changes

  // Update editor content when file changes (without recreating the editor)
  useEffect(() => {
    if (!viewRef.current || !currentFile) return;

    const currentContent = viewRef.current.state.doc.toString();
    if (currentContent !== currentFile.content) {
      // Update editor content without recreating the editor
      viewRef.current.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: currentFile.content
        }
      });
    }
  }, [currentFile.content, currentFile.id]);

  // Handle tab click
  const handleTabClick = useCallback((fileId: string) => {
    onFileActivate?.(fileId);
  }, [onFileActivate]);

  // Handle tab close
  const handleTabClose = useCallback((e: React.MouseEvent, fileId: string) => {
    e.stopPropagation();
    onFileClose?.(fileId);
  }, [onFileClose]);

  // Drag and Drop Handlers for file tabs
  const handleDragStart = useCallback((e: React.DragEvent, fileId: string) => {
    if (!enableDragDrop) return;
    setDraggedFile(fileId);
    e.dataTransfer.setData('application/icui-file', fileId);
    e.dataTransfer.effectAllowed = 'move';
  }, [enableDragDrop]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    if (!enableDragDrop) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, [enableDragDrop]);

  const handleDrop = useCallback((e: React.DragEvent, targetIndex: number) => {
    if (!enableDragDrop || !onFileReorder) return;
    e.preventDefault();
    const fileId = e.dataTransfer.getData('application/icui-file');
    if (fileId) {
      const draggedIndex = files.findIndex(file => file.id === fileId);
      if (draggedIndex !== -1 && draggedIndex !== targetIndex) {
        onFileReorder(draggedIndex, targetIndex);
      }
    }
    setDraggedFile(null);
    setDragOverIndex(null);
  }, [enableDragDrop, onFileReorder, files]);

  // Handle drag end to reset state
  const handleDragEnd = useCallback(() => {
    setDraggedFile(null);
    setDragOverIndex(null);
  }, []);

  // Handle save
  const handleSave = useCallback(() => {
    if (currentFile.modified) {
      onFileSave?.(currentFile.id);
    }
  }, [currentFile.id, currentFile.modified, onFileSave]);

  // Handle run
  const handleRun = useCallback(() => {
    const content = viewRef.current?.state.doc.toString() || currentFile.content;
    onFileRun?.(currentFile.id, content, currentFile.language);
  }, [currentFile.id, currentFile.language, onFileRun]);

  // Handle key shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 's') {
          e.preventDefault();
          handleSave();
        } else if (e.key === 'Enter') {
          e.preventDefault();
          handleRun();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleRun]);

  return (
    <div className={`flex flex-col h-full w-full ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Tab Bar */}
      {files.length > 0 && (
        <div className="flex items-center border-b overflow-x-auto overflow-y-hidden h-8 whitespace-nowrap" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)', userSelect: 'none' }}>
          <div className="flex min-w-0 flex-1">
            {files.map((file, index) => (
              <div
                key={file.id}
                className={`flex items-center px-3 py-1 border-r cursor-pointer hover:opacity-80 transition-opacity ${
                  file.id === activeFileId ? 'bg-opacity-20' : ''
                }${draggedFile === file.id ? ' dragging' : ''}`}
                style={{ 
                  backgroundColor: file.id === activeFileId ? 'var(--icui-bg-tertiary)' : 'transparent',
                  borderRightColor: 'var(--icui-border-subtle)',
                  color: 'var(--icui-text-primary)',
                  opacity: draggedFile === file.id ? 0.5 : 1,
                  cursor: enableDragDrop ? (draggedFile === file.id ? 'grabbing' : 'grab') : 'pointer',
                  userSelect: 'none',
                }}
                onClick={() => handleTabClick(file.id)}
                onDragStart={(e) => handleDragStart(e, file.id)}
                onDragEnd={handleDragEnd}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, index)}
                draggable={enableDragDrop}
              >
                <span className="text-sm font-medium truncate max-w-32">
                  {file.name}
                </span>
                {file.modified && (
                  <span className="ml-1 text-xs" style={{ color: 'var(--icui-warning)' }}>
                    ●
                  </span>
                )}
                {files.length > 1 && (
                  <button
                    className="ml-2 p-0.5 hover:opacity-60 transition-opacity"
                    onClick={(e) => handleTabClose(e, file.id)}
                    style={{ color: 'var(--icui-text-muted)' }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          {onFileCreate && (
            <button
              className="flex items-center px-2 py-1 hover:opacity-80 transition-opacity"
              onClick={onFileCreate}
              style={{ color: 'var(--icui-text-muted)' }}
            >
              <span className="text-sm">+</span>
            </button>
          )}
        </div>
      )}

      {/* Header removed for more code space */}

      {/* Editor Area - CodeMirror uses hardcoded dark colors, container uses CSS variables */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        <div ref={editorRef} className="h-full w-full" />
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>{currentFile.language} • {currentFile.name}</span>
        <span>
          Ctrl+S to save • Ctrl+Enter to run
          {autoSave && ' • Auto-save enabled'}
        </span>
      </div>
    </div>
  );
};

export default ICUIEditorPanel; 