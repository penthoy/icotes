/**
 * ICUI Editor Panel - From Scratch Implementation
 * A minimal Python code editor for the ICUI framework
 * Built from scratch without dependencies on CodeEditor.tsx
 */

import React, { useRef, useEffect, useState } from 'react';
import {
  EditorView,
  keymap,
  lineNumbers,
  drawSelection,
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
  defaultHighlightStyle,
  syntaxHighlighting,
  indentOnInput,
  bracketMatching,
  foldKeymap,
  foldGutter,
} from "@codemirror/language";
import { python } from '@codemirror/lang-python';

export interface ICUIEditorPanelFromScratchProps {
  className?: string;
}

const ICUIEditorPanelFromScratch: React.FC<ICUIEditorPanelFromScratchProps> = ({ 
  className = ''
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [content, setContent] = useState<string>(`# ICUIEditorPanel from scratch initialized!
# This is a minimal Python editor implementation

def hello_world():
    print("Hello from ICUI Editor!")
    return "Hello World!"

hello_world()

# Basic Python syntax highlighting test
class ExampleClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"

# Create instance and test
example = ExampleClass("ICUI")
print(example.greet())

# More Python features
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]
print(f"Squares: {squares}")

# Exception handling
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
finally:
    print("This always runs")
`);
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  // Detect theme on mount and when it changes
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
    
    // Create observer to watch for theme changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  // Initialize CodeMirror editor
  useEffect(() => {
    if (!editorRef.current) return;

    // Get current content from existing view if it exists
    const currentContent = viewRef.current?.state.doc.toString() || content;

    // Clean up existing view
    if (viewRef.current) {
      viewRef.current.destroy();
      viewRef.current = null;
    }

    // Create ICUI theme for CodeMirror
    const icuiTheme = EditorView.theme({
      '&': {
        color: 'var(--icui-text-primary)',
        backgroundColor: 'var(--icui-bg-primary)',
        fontSize: '14px',
        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
        height: '100%',
      },
      '.cm-content': {
        padding: '16px',
        caretColor: 'var(--icui-text-primary)',
        backgroundColor: 'var(--icui-bg-primary)',
        minHeight: '100%',
      },
      '.cm-focused .cm-cursor': {
        borderLeftColor: 'var(--icui-text-primary)',
      },
      '.cm-selectionBackground': {
        backgroundColor: 'var(--icui-accent-hover)',
      },
      '.cm-focused .cm-selectionBackground': {
        backgroundColor: 'var(--icui-accent-hover)',
      },
      '.cm-activeLine': {
        backgroundColor: 'var(--icui-bg-secondary)',
      },
      '.cm-gutters': {
        backgroundColor: 'var(--icui-bg-secondary)',
        color: 'var(--icui-text-muted)',
        border: 'none',
      },
      '.cm-activeLineGutter': {
        backgroundColor: 'var(--icui-bg-tertiary)',
      },
      '.cm-lineNumbers .cm-gutterElement': {
        color: 'var(--icui-text-muted)',
      },
      '.cm-foldPlaceholder': {
        backgroundColor: 'var(--icui-bg-tertiary)',
        border: 'none',
        color: 'var(--icui-text-secondary)',
      },
      '.cm-tooltip': {
        border: '1px solid var(--icui-border-subtle)',
        backgroundColor: 'var(--icui-bg-overlay)',
        color: 'var(--icui-text-primary)',
      },
      '.cm-scroller': {
        backgroundColor: 'var(--icui-bg-primary)',
      },
      '.cm-editor': {
        backgroundColor: 'var(--icui-bg-primary)',
      },
      '.cm-editor.cm-focused': {
        outline: 'none',
      },
    });

    // Create editor extensions
    const extensions = [
      lineNumbers(),
      foldGutter(),
      drawSelection(),
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
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      python(),
      icuiTheme,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          setContent(update.state.doc.toString());
        }
      }),
    ];

    // Create editor state with current content
    const state = EditorState.create({
      doc: currentContent,
      extensions,
    });

    // Create editor view
    const view = new EditorView({
      state,
      parent: editorRef.current,
    });

    viewRef.current = view;

    return () => {
      if (viewRef.current) {
        viewRef.current.destroy();
        viewRef.current = null;
      }
    };
  }, [isDarkTheme]); // Recreate editor when theme changes

  return (
    <div className="flex flex-col h-full w-full" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
            PYTHON
          </span>
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-muted)' }}>
            From Scratch
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
            Ready
          </span>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        <div 
          ref={editorRef} 
          className="h-full w-full"
          style={{ backgroundColor: 'var(--icui-bg-primary)' }}
        />
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>Python Editor</span>
        <span>From Scratch Implementation</span>
      </div>
    </div>
  );
};

export { ICUIEditorPanelFromScratch };
export default ICUIEditorPanelFromScratch; 