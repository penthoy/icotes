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
} from "@codemirror/language";
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
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),

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

      // Add theme conditionally
      if (theme === "dark") {
        extensions.push(oneDark);
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
    <div className="flex flex-col h-full bg-background">
      <div
        ref={editorRef}
        className="flex-grow overflow-auto font-mono text-sm h-full"
      />
    </div>
  );
};

export default CodeEditor;
