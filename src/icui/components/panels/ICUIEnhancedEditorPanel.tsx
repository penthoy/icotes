/**
 * ICUI Enhanced Editor Panel - Combined Implementation
 * Combines the best features from multiple implementations:
 * - Excellent syntax highlighting from ICUIEditorPanelFromScratch
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
import { createICUISyntaxHighlighting, createICUIEditorTheme, getLanguageExtension } from '../../utils/syntaxHighlighting';
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

export interface ICUIEnhancedEditorPanelProps {
  className?: string;
  files?: ICUIEditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, newContent: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileActivate?: (fileId: string) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

const ICUIEnhancedEditorPanel: React.FC<ICUIEnhancedEditorPanelProps> = ({
  className = '',
  files = [],
  activeFileId,
  onFileChange,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  onFileActivate,
  autoSave = false,
  autoSaveDelay = 1000,
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [isDarkTheme, setIsDarkTheme] = useState(false);
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

    // Create ICUI-compatible standalone theme colors
    const icuiThemeColors = {
      dark: {
        bg: '#1e1e1e',
        bgSecondary: '#2d2d2d',
        bgTertiary: '#3e3e3e',
        text: '#d4d4d4',
        textMuted: '#969696',
        textSecondary: '#cccccc',
        border: '#3e3e3e',
        borderSubtle: '#2d2d2d',
        accent: '#007acc',
        selection: '#264f78',
        activeLine: '#2a2a2a',
        gutter: '#1e1e1e',
      },
      light: {
        bg: '#ffffff',
        bgSecondary: '#f8f8f8',
        bgTertiary: '#e8e8e8',
        text: '#333333',
        textMuted: '#666666',
        textSecondary: '#555555',
        border: '#e1e1e1',
        borderSubtle: '#f0f0f0',
        accent: '#0066cc',
        selection: '#add6ff',
        activeLine: '#f5f5f5',
        gutter: '#f8f8f8',
      }
    };

    const themeColors = isDarkTheme ? icuiThemeColors.dark : icuiThemeColors.light;

    // Create enhanced theme for CodeMirror with hardcoded colors
    const enhancedTheme = EditorView.theme({
      '&': {
        color: themeColors.text,
        backgroundColor: themeColors.bg,
        fontSize: '14px',
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace',
        height: '100%',
      },
      '.cm-content': {
        padding: '16px',
        caretColor: themeColors.text,
        backgroundColor: themeColors.bg,
        minHeight: '100%',
      },
      '.cm-focused .cm-cursor': {
        borderLeftColor: themeColors.text,
      },
      '.cm-selectionBackground, .cm-line::selection, .cm-content ::selection, .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: `${themeColors.selection} !important`,
        color: 'inherit',
        backgroundImage: 'none !important',
      },
      '.cm-focused .cm-selectionBackground, .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: `${themeColors.selection} !important`,
        color: 'inherit',
        backgroundImage: 'none !important',
      },
      '.cm-activeLine': {
        backgroundColor: themeColors.activeLine,
      },
      '.cm-gutters': {
        backgroundColor: themeColors.gutter,
        color: themeColors.textMuted,
        border: 'none',
      },
      '.cm-activeLineGutter': {
        backgroundColor: themeColors.bgTertiary,
      },
      '.cm-lineNumbers .cm-gutterElement': {
        color: themeColors.textMuted,
      },
      '.cm-foldPlaceholder': {
        backgroundColor: themeColors.bgTertiary,
        border: 'none',
        color: themeColors.textSecondary,
      },
      '.cm-tooltip': {
        border: `1px solid ${themeColors.border}`,
        backgroundColor: themeColors.bgSecondary,
        color: themeColors.text,
      },
      '.cm-scroller': {
        backgroundColor: themeColors.bg,
      },
      '.cm-editor': {
        backgroundColor: themeColors.bg,
      },
      '.cm-editor.cm-focused': {
        outline: 'none',
      },
      '.cm-tooltip-autocomplete': {
        '& > ul > li[aria-selected]': {
          backgroundColor: themeColors.accent,
          color: themeColors.bg,
        }
      },
    });

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
        <div className="flex items-center border-b overflow-x-auto" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
          <div className="flex min-w-0 flex-1">
            {files.map((file) => (
              <div
                key={file.id}
                className={`flex items-center px-4 py-2 border-r cursor-pointer hover:opacity-80 transition-opacity ${
                  file.id === activeFileId ? 'bg-opacity-20' : ''
                }`}
                style={{ 
                  backgroundColor: file.id === activeFileId ? 'var(--icui-bg-tertiary)' : 'transparent',
                  borderRightColor: 'var(--icui-border-subtle)',
                  color: 'var(--icui-text-primary)'
                }}
                onClick={() => handleTabClick(file.id)}
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
                    className="ml-2 p-1 hover:opacity-60 transition-opacity"
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
              className="flex items-center px-3 py-2 hover:opacity-80 transition-opacity"
              onClick={onFileCreate}
              style={{ color: 'var(--icui-text-muted)' }}
            >
              <span className="text-sm">+</span>
            </button>
          )}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
            {currentFile.language.toUpperCase()}
          </span>
          <span className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
            {currentFile.name}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          {currentFile.modified && (
            <span className="text-xs" style={{ color: 'var(--icui-warning)' }}>
              Modified
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!currentFile.modified}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              currentFile.modified 
                ? 'opacity-100 hover:opacity-80' 
                : 'opacity-50 cursor-not-allowed'
            }`}
            style={{ 
              backgroundColor: currentFile.modified ? 'var(--icui-success)' : 'var(--icui-bg-tertiary)',
              color: 'var(--icui-text-primary)'
            }}
          >
            Save
          </button>
          <button
            onClick={handleRun}
            className="px-3 py-1 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor Area - Only the editor uses hardcoded colors */}
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

export default ICUIEnhancedEditorPanel; 