/**
 * CodeMirror Extensions Factory
 * 
 * Creates editor extensions including syntax highlighting, diff decorations,
 * keybindings, and theme configuration
 */

import {
  EditorView,
  keymap,
  lineNumbers,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
  ViewPlugin,
  Decoration,
  ViewUpdate
} from "@codemirror/view";
import { Extension } from "@codemirror/state";
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
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { markdown } from '@codemirror/lang-markdown';
import { json } from '@codemirror/lang-json';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { cpp } from '@codemirror/lang-cpp';
import { rust } from '@codemirror/lang-rust';
import { go } from '@codemirror/lang-go';
import { StreamLanguage } from '@codemirror/language';
import { yaml } from '@codemirror/legacy-modes/mode/yaml';
import { shell } from '@codemirror/legacy-modes/mode/shell';
import { createICUISyntaxHighlighting, createICUIEnhancedEditorTheme } from '../../../utils/syntaxHighlighting';
import { EditorFile } from '../types';

interface CreateExtensionsOptions {
  file: EditorFile | undefined;
  isDarkTheme: boolean;
  saveHandlerRef: React.RefObject<() => void | Promise<void>>;
  contentChangeHandlerRef: React.RefObject<((content: string) => void) | null>;
  currentContentRef: React.MutableRefObject<string>;
}

/**
 * Get language extension for syntax highlighting
 */
function getLanguageExtension(language: string): Extension {
  const langMap: Record<string, () => Extension> = {
    python: () => python(),
    javascript: () => javascript(),
    typescript: () => javascript({ typescript: true }),
    markdown: () => markdown(),
    json: () => json(),
    html: () => html(),
    css: () => css(),
    yaml: () => StreamLanguage.define(yaml),
    shell: () => StreamLanguage.define(shell),
    cpp: () => cpp(),
    rust: () => rust(),
    go: () => go(),
  };

  const langFn = langMap[language];
  return langFn ? langFn() : [];
}

/**
 * Create diff highlighting decorations
 */
function createDiffDecorations(file: EditorFile | undefined): Extension {
  if (!file || file.language !== 'diff') return [];

  const added = Decoration.line({ class: 'cm-diff-added' });
  const removed = Decoration.line({ class: 'cm-diff-removed' });
  const hunk = Decoration.line({ class: 'cm-diff-hunk' });
  const meta = file.__diffMeta || { 
    added: new Set<number>(), 
    removed: new Set<number>(), 
    hunk: new Set<number>() 
  };

  return ViewPlugin.fromClass(class {
    decorations: any;
    
    constructor(view: EditorView) { 
      this.decorations = this.build(view); 
    }
    
    update(u: ViewUpdate) { 
      if (u.docChanged) this.decorations = this.build(u.view); 
    }
    
    build(view: EditorView) {
      const ranges: any[] = [];
      for (let i = 1; i <= view.state.doc.lines; i++) {
        if (meta.hunk.has(i)) {
          ranges.push(hunk.range(view.state.doc.line(i).from));
        } else if (meta.added.has(i)) {
          ranges.push(added.range(view.state.doc.line(i).from));
        } else if (meta.removed.has(i)) {
          ranges.push(removed.range(view.state.doc.line(i).from));
        }
      }
      return Decoration.set(ranges);
    }
  }, {
    decorations: v => v.decorations
  });
}

/**
 * Create all CodeMirror extensions for the editor
 */
export function createEditorExtensions({
  file,
  isDarkTheme,
  saveHandlerRef,
  contentChangeHandlerRef,
  currentContentRef
}: CreateExtensionsOptions): Extension[] {
  const language = file?.language || 'text';
  
  const extensions: Extension[] = [
    // Basic editor features
    lineNumbers(),
    foldGutter(),
    dropCursor(),
    indentOnInput(),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    rectangularSelection(),
    crosshairCursor(),
    highlightSelectionMatches(),
    history(),
    
    // Keybindings
    keymap.of([
      {
        key: 'Mod-s',
        run: () => {
          try {
            const fn = saveHandlerRef.current;
            if (fn) fn();
          } catch (e) {
            console.warn('Save shortcut failed:', e);
          }
          return true; // Prevent browser default
        }
      },
      ...closeBracketsKeymap,
      ...defaultKeymap,
      ...searchKeymap,
      ...historyKeymap,
      ...foldKeymap,
      ...completionKeymap,
      indentWithTab,
    ]),
    
    // Syntax highlighting and theme
    syntaxHighlighting(createICUISyntaxHighlighting(isDarkTheme)),
    EditorView.theme(createICUIEnhancedEditorTheme(isDarkTheme)),
    
    // Language-specific extension
    getLanguageExtension(language),
    
    // Content change listener
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        const newContent = update.state.doc.toString();
        if (newContent !== currentContentRef.current) {
          currentContentRef.current = newContent;
          if (contentChangeHandlerRef.current) {
            contentChangeHandlerRef.current(newContent);
          }
        }
      }
    }),
    
    // Diff highlighting
    createDiffDecorations(file),
  ];

  return extensions;
}
