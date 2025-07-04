import React, { useEffect, useRef, useState } from "react";
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

  const getLanguageExtension = (lang: SupportedLanguage) => {
    switch (lang) {
      case 'javascript':
        return javascript();
      case 'python':
        return python();
      default:
        return python();
    }
  };

  // Initialize editor only once
  useEffect(() => {
    if (!editorRef.current || editorView) return;

    try {
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

        // Update listener
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newCode = update.state.doc.toString();
            setInternalCode(newCode);
            setCode?.(newCode);
            onCodeChange?.(newCode);
          }
        }),
      ];

      // Add theme conditionally
      if (theme === "dark") {
        extensions.push(oneDark);
      }

      // Create initial state
      const initialState = EditorState.create({
        doc: propCode || initialCode,
        extensions,
      });

      // Create a new editor instance
      const view = new EditorView({
        state: initialState,
        parent: editorRef.current,
      });

      setEditorView(view);

      return () => {
        view.destroy();
      };
    } catch (error) {
      console.error("Error creating CodeMirror editor:", error);
      console.error("Error stack:", error.stack);
    }
  }, [theme, initialCode, language]);

  // Update editor content when propCode changes (without recreating editor)
  useEffect(() => {
    if (!editorView || !propCode) return;
    
    const currentContent = editorView.state.doc.toString();
    if (currentContent !== propCode) {
      const transaction = editorView.state.update({
        changes: { from: 0, to: currentContent.length, insert: propCode }
      });
      editorView.dispatch(transaction);
    }
  }, [propCode, editorView]);

  // Update theme without recreating editor
  useEffect(() => {
    if (!editorView) return;
    
    // For theme changes, we need to recreate the editor
    // This is less frequent than content changes
    editorView.destroy();
    setEditorView(null);
    
    // The editor will be recreated by the first useEffect
  }, [theme]);

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
