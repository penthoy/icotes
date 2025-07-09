import React, { useEffect, useRef, useState, useCallback } from "react";
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
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import { Button } from "./ui/button";

export type SupportedLanguage = 'javascript' | 'python';

interface CodeEditorProps {
  code?: string;
  setCode?: (code: string) => void;
  theme?: "light" | "dark";
  onCodeChange?: (code: string) => void;
  initialCode?: string;
  onRun?: (code: string) => void;
  language?: SupportedLanguage;
}

// Create light theme syntax highlighting
const lightHighlightStyle = HighlightStyle.define([
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

// Create dark theme syntax highlighting
const darkHighlightStyle = HighlightStyle.define([
  { tag: t.keyword, color: "#569cd6" },
  { tag: [t.name, t.deleted, t.character, t.propertyName, t.macroName], color: "#4ec9b0" },
  { tag: [t.function(t.variableName), t.labelName], color: "#dcdcaa" },
  { tag: [t.color, t.constant(t.name), t.standard(t.name)], color: "#4fc1ff" },
  { tag: [t.definition(t.name), t.separator], color: "#9cdcfe" },
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

// Custom light theme for CodeMirror using ICUI theme variables
const icuiLightTheme = EditorView.theme({
  '&': {
    color: 'var(--icui-text-primary)',
    backgroundColor: 'var(--icui-bg-primary)',
  },
  '.cm-content': {
    padding: '16px',
    caretColor: 'var(--icui-text-primary)',
    backgroundColor: 'var(--icui-bg-primary)',
  },
  '.cm-focused .cm-cursor': {
    borderLeftColor: 'var(--icui-text-primary)',
  },
  '.cm-selectionBackground, .cm-line::selection, .cm-content ::selection, .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--icui-selection-bg) !important',
    color: 'inherit',
  },
  '.cm-focused .cm-selectionBackground, .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--icui-selection-bg) !important',
    color: 'inherit',
  },
  '.cm-panels': {
    backgroundColor: 'var(--icui-bg-secondary)',
    color: 'var(--icui-text-primary)',
  },
  '.cm-panels.cm-panels-top': {
    borderBottom: '2px solid var(--icui-border)',
  },
  '.cm-panels.cm-panels-bottom': {
    borderTop: '2px solid var(--icui-border)',
  },
  '.cm-searchMatch': {
    backgroundColor: 'var(--icui-warning)',
    color: 'var(--icui-bg-primary)',
  },
  '.cm-searchMatch.cm-searchMatch-selected': {
    backgroundColor: 'var(--icui-accent)',
  },
  '.cm-activeLine': {
    backgroundColor: 'var(--icui-bg-secondary)',
  },
  '.cm-selectionMatch': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '&.cm-focused .cm-matchingBracket, &.cm-focused .cm-nonmatchingBracket': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--icui-bg-secondary)',
    color: 'var(--icui-text-muted)',
    border: 'none',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '.cm-foldPlaceholder': {
    backgroundColor: 'var(--icui-bg-tertiary)',
    border: 'none',
    color: 'var(--icui-text-secondary)',
  },
  '.cm-tooltip': {
    border: '1px solid var(--icui-border)',
    backgroundColor: 'var(--icui-bg-overlay)',
    color: 'var(--icui-text-primary)',
  },
  '.cm-tooltip .cm-tooltip-arrow:before': {
    borderTopColor: 'var(--icui-border)',
  },
  '.cm-tooltip .cm-tooltip-arrow:after': {
    borderTopColor: 'var(--icui-bg-overlay)',
  },
  '.cm-tooltip-autocomplete': {
    '& > ul > li[aria-selected]': {
      backgroundColor: 'var(--icui-accent)',
      color: 'white',
    }
  },
  '.cm-content ::selection': {
    backgroundColor: 'var(--icui-selection-bg) !important',
  },
}, { dark: false });

// Custom dark theme for CodeMirror using ICUI theme variables
const icuiDarkTheme = EditorView.theme({
  '&': {
    color: 'var(--icui-text-primary)',
    backgroundColor: 'var(--icui-bg-primary)',
  },
  '.cm-content': {
    padding: '16px',
    caretColor: 'var(--icui-text-primary)',
    backgroundColor: 'var(--icui-bg-primary)',
  },
  '.cm-focused .cm-cursor': {
    borderLeftColor: 'var(--icui-text-primary)',
  },
  '.cm-selectionBackground, .cm-line::selection, .cm-content ::selection, .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--icui-selection-bg) !important',
    color: 'inherit',
  },
  '.cm-focused .cm-selectionBackground, .cm-selectionLayer .cm-selectionBackground': {
    backgroundColor: 'var(--icui-selection-bg) !important',
    color: 'inherit',
  },
  '.cm-panels': {
    backgroundColor: 'var(--icui-bg-secondary)',
    color: 'var(--icui-text-primary)',
  },
  '.cm-panels.cm-panels-top': {
    borderBottom: '2px solid var(--icui-border)',
  },
  '.cm-panels.cm-panels-bottom': {
    borderTop: '2px solid var(--icui-border)',
  },
  '.cm-searchMatch': {
    backgroundColor: 'var(--icui-warning)',
    color: 'var(--icui-bg-primary)',
  },
  '.cm-searchMatch.cm-searchMatch-selected': {
    backgroundColor: 'var(--icui-accent)',
  },
  '.cm-activeLine': {
    backgroundColor: 'var(--icui-bg-secondary)',
  },
  '.cm-selectionMatch': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '&.cm-focused .cm-matchingBracket, &.cm-focused .cm-nonmatchingBracket': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--icui-bg-secondary)',
    color: 'var(--icui-text-muted)',
    border: 'none',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'var(--icui-bg-tertiary)',
  },
  '.cm-foldPlaceholder': {
    backgroundColor: 'var(--icui-bg-tertiary)',
    border: 'none',
    color: 'var(--icui-text-secondary)',
  },
  '.cm-tooltip': {
    border: '1px solid var(--icui-border)',
    backgroundColor: 'var(--icui-bg-overlay)',
    color: 'var(--icui-text-primary)',
  },
  '.cm-tooltip .cm-tooltip-arrow:before': {
    borderTopColor: 'var(--icui-border)',
  },
  '.cm-tooltip .cm-tooltip-arrow:after': {
    borderTopColor: 'var(--icui-bg-overlay)',
  },
  '.cm-tooltip-autocomplete': {
    '& > ul > li[aria-selected]': {
      backgroundColor: 'var(--icui-accent)',
      color: 'white',
    }
  },
  '.cm-content ::selection': {
    backgroundColor: 'var(--icui-selection-bg) !important',
  },
}, { dark: true });

const CodeEditor = ({
  code: propCode,
  setCode,
  theme = "light",
  onCodeChange,
  initialCode = '# Write your Python code here\nprint("Hello, world!")',
  onRun,
  language = 'python',
}: CodeEditorProps) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [editorView, setEditorView] = useState<EditorView | null>(null);
  const [code, setInternalCode] = useState<string>(propCode || initialCode);

  const getLanguageExtension = useCallback((lang: SupportedLanguage) => {
    switch (lang) {
      case 'javascript':
        return javascript();
      case 'python':
        return python();
      default:
        return python();
    }
  }, []);

  // Initialize editor when needed and recreate when theme or language changes
  useEffect(() => {
    if (!editorRef.current) return;

    // Destroy existing editor if it exists
    if (editorView) {
      editorView.destroy();
      setEditorView(null);
    }

    try {
      // Get the current content to preserve during recreation
      const currentContent = propCode || code || initialCode;

      // Create extensions array manually (replacing basicSetup)
      const extensions: Extension[] = [
        // Basic editor setup
        lineNumbers(),
        foldGutter(),
        drawSelection(),
        dropCursor(),
        indentOnInput(),
        bracketMatching(),
        closeBrackets(),
        autocompletion(),
        rectangularSelection(),
        crosshairCursor(),
        highlightSelectionMatches(),
        history(),

        // Language support
        getLanguageExtension(language),

        // Keymaps
        keymap.of([
          ...closeBracketsKeymap,
          ...defaultKeymap,
          ...searchKeymap,
          ...historyKeymap,
          ...foldKeymap,
          ...completionKeymap,
          indentWithTab,
        ]),

        // Update listener with debouncing to prevent performance issues
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newCode = update.state.doc.toString();
            // Use a single batch update to prevent multiple re-renders
            requestAnimationFrame(() => {
              setInternalCode(newCode);
              setCode?.(newCode);
              onCodeChange?.(newCode);
            });
          }
        }),
      ];

      // Add theme and syntax highlighting conditionally
      if (theme === "dark") {
        extensions.push(icuiDarkTheme);
        extensions.push(syntaxHighlighting(darkHighlightStyle));
      } else {
        extensions.push(icuiLightTheme);
        extensions.push(syntaxHighlighting(lightHighlightStyle));
      }

      // Create initial state with current content
      const initialState = EditorState.create({
        doc: currentContent,
        extensions,
      });

      // Create a new editor instance
      const view = new EditorView({
        state: initialState,
        parent: editorRef.current,
      });

      setEditorView(view);
      
      // Update internal code state to match editor content
      setInternalCode(currentContent);

      return () => {
        view.destroy();
      };
    } catch (error) {
      console.error("Error creating CodeMirror editor:", error);
      console.error("Error stack:", error.stack);
    }
  }, [theme, language, getLanguageExtension]);

  // Update editor content when propCode changes (without recreating editor)
  useEffect(() => {
    if (!editorView || propCode === undefined) return;
    
    const currentContent = editorView.state.doc.toString();
    if (currentContent !== propCode) {
      const transaction = editorView.state.update({
        changes: { from: 0, to: currentContent.length, insert: propCode }
      });
      editorView.dispatch(transaction);
      setInternalCode(propCode);
    }
  }, [propCode, editorView]);

  // Clean up editor on unmount
  useEffect(() => {
    return () => {
      if (editorView) {
        editorView.destroy();
      }
    };
  }, []);

  const handleRunCode = () => {
    onRun?.(code);
  };

  return (
    <div 
      className="flex flex-col h-full"
      style={{ 
        backgroundColor: 'var(--icui-bg-primary)',
        color: 'var(--icui-text-primary)'
      }}
    >
      <div
        ref={editorRef}
        className="flex-grow overflow-auto font-mono text-sm h-full"
        style={{ 
          backgroundColor: 'var(--icui-bg-primary)',
          minHeight: "100%"
        }}
      />
    </div>
  );
};

export default CodeEditor;
