import React, { useEffect, useRef, useState } from "react";
import { EditorView, keymap, lineNumbers, drawSelection, dropCursor, rectangularSelection, crosshairCursor } from "@codemirror/view";
import { EditorState, Extension } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { defaultHighlightStyle, syntaxHighlighting, indentOnInput, bracketMatching, foldKeymap, foldGutter } from "@codemirror/language";
import { javascript } from "@codemirror/lang-javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import { Button } from "./ui/button";

interface CodeEditorProps {
  code?: string;
  setCode?: (code: string) => void;
  theme?: "light" | "dark";
  onCodeChange?: (code: string) => void;
  initialCode?: string;
  onRun?: (code: string) => void;
}

const CodeEditor = ({
  code: propCode,
  setCode,
  theme = "light",
  onCodeChange,
  initialCode = '// Write your JavaScript code here\nconsole.log("Hello, world!");',
  onRun,
}: CodeEditorProps) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const [editorView, setEditorView] = useState<EditorView | null>(null);
  const [code, setInternalCode] = useState<string>(propCode || initialCode);

  useEffect(() => {
    if (!editorRef.current) return;

    // Clean up any existing editor instance
    if (editorView) {
      editorView.destroy();
    }

    console.log('Creating CodeMirror extensions...');
    console.log('Available packages:', {
      EditorView: typeof EditorView,
      EditorState: typeof EditorState,
      javascript: typeof javascript,
      oneDark: typeof oneDark
    });
    
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
        javascript(),
        
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

      console.log('Extensions created:', extensions.length);

      // Add theme conditionally
      if (theme === "dark") {
        extensions.push(oneDark);
        console.log('Added dark theme');
      }

      // Create initial state
      const initialState = EditorState.create({
        doc: propCode || initialCode,
        extensions,
      });

      console.log('Initial state created:', initialState);

      // Create a new editor instance
      const view = new EditorView({
        state: initialState,
        parent: editorRef.current,
      });

      console.log('EditorView created successfully:', view);
      console.log('Extensions used:', extensions.length);

      setEditorView(view);

      return () => {
        view.destroy();
      };
    } catch (error) {
      console.error('Error creating CodeMirror editor:', error);
      console.error('Error stack:', error.stack);
    }
  }, [theme, propCode, initialCode]);

  const handleRunCode = () => {
    onRun?.(code);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      <div className="flex justify-end p-2 border-b">
        <Button
          onClick={handleRunCode}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          Run
        </Button>
      </div>
      <div
        ref={editorRef}
        className="flex-grow overflow-auto font-mono text-sm"
        style={{ height: "calc(100% - 50px)" }}
      />
    </div>
  );
};

export default CodeEditor;
