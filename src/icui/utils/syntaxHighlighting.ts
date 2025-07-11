/**
 * ICUI Syntax Highlighting Utilities
 * Reusable syntax highlighting configurations for CodeMirror
 */

import { HighlightStyle } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags as t } from "@lezer/highlight";

// Hardcoded theme colors for CodeMirror (independent of CSS variables)
// Using darker colors similar to the from-scratch editor for better dark theme
export const ICUI_EDITOR_THEME_COLORS = {
  dark: {
    bg: '#111827',      // Much darker - similar to gray-900
    bgSecondary: '#1f2937',  // Darker secondary - similar to gray-800
    bgTertiary: '#374151',   // Darker tertiary - similar to gray-700
    text: '#f9fafb',         // Lighter text - similar to gray-100
    textMuted: '#9ca3af',    // Muted text - similar to gray-400
    textSecondary: '#e5e7eb', // Secondary text - similar to gray-200
    border: '#374151',       // Border - similar to gray-700
    borderSubtle: '#1f2937', // Subtle border - similar to gray-800
    accent: '#3b82f6',       // Blue accent
    selection: '#1e40af',    // Blue selection
    activeLine: '#1f2937',   // Active line - similar to gray-800
    gutter: '#1f2937',       // Gutter - similar to gray-800
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

// Create syntax highlighting styles optimized for ICUI themes
export const createICUISyntaxHighlighting = (isDark: boolean) => {
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

// Create ICUI-themed CodeMirror theme using CSS variables
export const createICUIEditorTheme = (isDark: boolean) => {
  return {
    '&': {
      color: 'var(--icui-text-primary)',
      backgroundColor: 'var(--icui-bg-primary)',
      fontSize: '14px',
      fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace',
      height: '100%',
    },
    '.cm-content': {
      padding: '16px',
      caretColor: 'var(--icui-text-primary)',
      backgroundColor: 'var(--icui-bg-primary)',
      minHeight: '100%',
    },
    '.cm-focused': {
      outline: 'none',
    },
    '.cm-editor': {
      backgroundColor: 'var(--icui-bg-primary)',
    },
    '.cm-scroller': {
      backgroundColor: 'var(--icui-bg-primary)',
    },
    '.cm-gutter': {
      backgroundColor: 'var(--icui-bg-secondary)',
      color: 'var(--icui-text-muted)',
      borderRight: '1px solid var(--icui-border-subtle)',
    },
    '.cm-lineNumbers': {
      color: 'var(--icui-text-muted)',
      fontSize: '12px',
    },
    '.cm-gutters': {
      backgroundColor: 'var(--icui-bg-secondary)',
      borderRight: '1px solid var(--icui-border-subtle)',
    },
    '.cm-activeLine': {
      backgroundColor: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
    },
    '.cm-activeLineGutter': {
      backgroundColor: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
    },
    '.cm-selectionMatch': {
      backgroundColor: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
    },
    '.cm-searchMatch': {
      backgroundColor: isDark ? 'rgba(255, 255, 0, 0.2)' : 'rgba(255, 255, 0, 0.3)',
    },
    '.cm-searchMatch.cm-searchMatch-selected': {
      backgroundColor: isDark ? 'rgba(255, 255, 0, 0.3)' : 'rgba(255, 255, 0, 0.5)',
    },
    '.cm-cursor': {
      borderLeft: '2px solid var(--icui-text-primary)',
    },
    '.cm-dropCursor': {
      borderLeft: '2px solid var(--icui-accent)',
    },
    '.cm-tooltip': {
      backgroundColor: 'var(--icui-bg-overlay)',
      color: 'var(--icui-text-primary)',
      border: '1px solid var(--icui-border-subtle)',
      borderRadius: '4px',
    },
    '.cm-tooltip.cm-tooltip-autocomplete': {
      backgroundColor: 'var(--icui-bg-overlay)',
    },
    '.cm-tooltip-autocomplete ul li': {
      color: 'var(--icui-text-primary)',
    },
    '.cm-tooltip-autocomplete ul li[aria-selected]': {
      backgroundColor: 'var(--icui-accent)',
      color: 'var(--icui-text-primary)',
    },
  };
};

// Create enhanced CodeMirror theme with hardcoded colors (for consistent editor appearance)
export const createICUIEnhancedEditorTheme = (isDark: boolean) => {
  const themeColors = isDark ? ICUI_EDITOR_THEME_COLORS.dark : ICUI_EDITOR_THEME_COLORS.light;

  // Map key colors to CSS variables so background synchronises with current theme
  const cssVars = {
    bg: 'var(--icui-bg-primary)',
    bgSecondary: 'var(--icui-bg-secondary)',
    bgTertiary: 'var(--icui-bg-tertiary)',
    text: 'var(--icui-text-primary)',
    textMuted: 'var(--icui-text-muted)',
    border: 'var(--icui-border-subtle)',
  } as const;

  return {
    '&': {
      color: cssVars.text,
      backgroundColor: cssVars.bg,
      fontSize: '14px',
      fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace',
      height: '100%',
    },
    '.cm-content': {
      // Reduce padding for tighter look (especially left side)
      padding: '4px 8px',
      caretColor: cssVars.text,
      backgroundColor: cssVars.bg,
      minHeight: '100%',
    },
    '.cm-focused .cm-cursor': {
      borderLeftColor: cssVars.text,
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
      backgroundColor: cssVars.bgSecondary,
      color: cssVars.textMuted,
      border: 'none',
      paddingLeft: '4px',
    },
    '.cm-lineNumbers': {
      // Slightly smaller gutter width
      minWidth: '32px',
    },
    '.cm-lineNumbers .cm-gutterElement': {
      padding: '0 4px',
    },
    '.cm-activeLineGutter': {
      backgroundColor: cssVars.bgTertiary,
    },
    '.cm-foldPlaceholder': {
      backgroundColor: themeColors.bgTertiary,
      border: 'none',
      color: themeColors.textSecondary,
    },
    '.cm-tooltip': {
      border: `1px solid ${cssVars.border}`,
      backgroundColor: cssVars.bgSecondary,
      color: cssVars.text,
    },
    '.cm-scroller': {
      backgroundColor: cssVars.bg,
    },
    '.cm-editor': {
      backgroundColor: cssVars.bg,
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
  };
};

// Language extension mapping
export const getLanguageExtension = (language: string) => {
  switch (language.toLowerCase()) {
    case 'python':
      return import('@codemirror/lang-python').then(mod => mod.python());
    case 'javascript':
      return import('@codemirror/lang-javascript').then(mod => mod.javascript());
    case 'typescript':
      return import('@codemirror/lang-javascript').then(mod => mod.javascript({ typescript: true }));
    case 'html':
      // HTML support via legacy modes or basic text
      return Promise.resolve(null);
    case 'css':
      // CSS support via legacy modes or basic text
      return Promise.resolve(null);
    case 'json':
      // JSON support via legacy modes or basic text
      return Promise.resolve(null);
    case 'markdown':
      // Markdown support via legacy modes or basic text
      return Promise.resolve(null);
    default:
      return Promise.resolve(null);
  }
}; 