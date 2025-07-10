/**
 * ICUI Editor Panel - From Scratch Implementation
 * A minimal Python code editor for the ICUI framework
 * Built from scratch without dependencies on CodeEditor.tsx
 * Uses standalone styles independent of ICUI CSS variables for comparison
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
  HighlightStyle,
} from "@codemirror/language";
import { tags as t } from "@lezer/highlight";
import { python } from '@codemirror/lang-python';

export interface ICUIEditorPanelFromScratchProps {
  className?: string;
}

// Standalone color themes (not using ICUI variables)
const STANDALONE_THEMES = {
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
    accentHover: '#1177bb',
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
    accentHover: '#004499',
    selection: '#add6ff',
    activeLine: '#f5f5f5',
    gutter: '#f8f8f8',
  }
};

// Standalone syntax highlighting styles
const createStandaloneSyntaxHighlighting = (isDark: boolean) => {
  if (isDark) {
    return HighlightStyle.define([
      { tag: t.keyword, color: "#569cd6" },
      { tag: [t.name, t.deleted, t.character, t.propertyName, t.macroName], color: "#9cdcfe" },
      { tag: [t.function(t.variableName), t.labelName], color: "#dcdcaa" },
      { tag: [t.color, t.constant(t.name), t.standard(t.name)], color: "#4fc1ff" },
      { tag: [t.definition(t.name), t.separator], color: "#4ec9b0" },
      { tag: [t.typeName, t.className, t.number, t.changed, t.annotation, t.modifier, t.self, t.namespace], color: "#4ec9b0" },
      { tag: [t.operator, t.operatorKeyword, t.url, t.escape, t.regexp, t.link, t.special(t.string)], color: "#d16969" },
      { tag: [t.meta, t.comment], color: "#6a9955" },
      { tag: t.strong, fontWeight: "bold" },
      { tag: t.emphasis, fontStyle: "italic" },
      { tag: t.strikethrough, textDecoration: "line-through" },
      { tag: t.link, color: "#569cd6", textDecoration: "underline" },
      { tag: t.heading, fontWeight: "bold", color: "#569cd6" },
      { tag: [t.atom, t.bool, t.special(t.variableName)], color: "#dcdcaa" },
      { tag: [t.processingInstruction, t.string, t.inserted], color: "#ce9178" },
      { tag: t.invalid, color: "#f44747" },
    ]);
  } else {
    return HighlightStyle.define([
      { tag: t.keyword, color: "#0000ff" },
      { tag: [t.name, t.deleted, t.character, t.propertyName, t.macroName], color: "#008080" },
      { tag: [t.function(t.variableName), t.labelName], color: "#795e26" },
      { tag: [t.color, t.constant(t.name), t.standard(t.name)], color: "#0e07d3" },
      { tag: [t.definition(t.name), t.separator], color: "#001080" },
      { tag: [t.typeName, t.className, t.number, t.changed, t.annotation, t.modifier, t.self, t.namespace], color: "#267f99" },
      { tag: [t.operator, t.operatorKeyword, t.url, t.escape, t.regexp, t.link, t.special(t.string)], color: "#a31515" },
      { tag: [t.meta, t.comment], color: "#008000" },
      { tag: t.strong, fontWeight: "bold" },
      { tag: t.emphasis, fontStyle: "italic" },
      { tag: t.strikethrough, textDecoration: "line-through" },
      { tag: t.link, color: "#0000ee", textDecoration: "underline" },
      { tag: t.heading, fontWeight: "bold", color: "#0000ff" },
      { tag: [t.atom, t.bool, t.special(t.variableName)], color: "#795e26" },
      { tag: [t.processingInstruction, t.string, t.inserted], color: "#a31515" },
      { tag: t.invalid, color: "#ff0000" },
    ]);
  }
};

const ICUIEditorPanelFromScratch: React.FC<ICUIEditorPanelFromScratchProps> = ({ 
  className = ''
}) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const [content, setContent] = useState<string>(`# ICUIEditorPanel from scratch initialized!
# This is a minimal Python editor implementation with standalone styles

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

# Test various Python constructs
import os
from datetime import datetime

def process_data(data_list):
    """Process a list of data items."""
    processed = []
    for item in data_list:
        if isinstance(item, str):
            processed.append(item.upper())
        elif isinstance(item, (int, float)):
            processed.append(item * 2)
        else:
            processed.append(str(item))
    return processed

# Lambda functions
multiply = lambda x, y: x * y
result = multiply(5, 3)

# List comprehensions
evens = [x for x in range(20) if x % 2 == 0]
print(f"Even numbers: {evens}")

# Dictionary comprehensions
squares_dict = {x: x**2 for x in range(5)}
print(f"Squares dict: {squares_dict}")

# Generator expressions
sum_squares = sum(x**2 for x in range(10))
print(f"Sum of squares: {sum_squares}")
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

    // Get standalone theme colors
    const themeColors = isDarkTheme ? STANDALONE_THEMES.dark : STANDALONE_THEMES.light;

    // Create standalone theme for CodeMirror (no ICUI variables)
    const standaloneTheme = EditorView.theme({
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
      '.cm-selectionBackground': {
        backgroundColor: themeColors.selection,
      },
      '.cm-focused .cm-selectionBackground': {
        backgroundColor: themeColors.selection,
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

    // Create standalone syntax highlighting
    const standaloneSyntaxHighlighting = createStandaloneSyntaxHighlighting(isDarkTheme);

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
      syntaxHighlighting(standaloneSyntaxHighlighting, { fallback: true }),
      python(),
      standaloneTheme,
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

  // Get standalone theme colors for UI
  const themeColors = isDarkTheme ? STANDALONE_THEMES.dark : STANDALONE_THEMES.light;

  return (
    <div className="flex flex-col h-full w-full" style={{ backgroundColor: themeColors.bg }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: themeColors.bgSecondary, borderBottomColor: themeColors.borderSubtle }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: themeColors.text }}>
            PYTHON
          </span>
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: themeColors.bgTertiary, color: themeColors.textMuted }}>
            Standalone Styles
          </span>
          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: themeColors.accent, color: themeColors.bg }}>
            No ICUI Variables
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs" style={{ color: themeColors.textMuted }}>
            {isDarkTheme ? 'Dark Theme' : 'Light Theme'}
          </span>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: themeColors.bg }}>
        <div 
          ref={editorRef} 
          className="h-full w-full"
          style={{ backgroundColor: themeColors.bg }}
        />
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: themeColors.bgSecondary, borderTopColor: themeColors.borderSubtle, color: themeColors.textMuted }}>
        <span>Python Editor - Standalone Styles</span>
        <span>Independent of ICUI CSS Variables</span>
      </div>
    </div>
  );
};

export { ICUIEditorPanelFromScratch };
export default ICUIEditorPanelFromScratch; 