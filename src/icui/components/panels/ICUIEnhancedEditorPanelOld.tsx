/**
 * ICUI Enhanced Editor Panel - Reference Implementation
 * A minimal, working code editor for the ICUI framework
 * Following the same pattern as ICUITerminalPanel
 */

import React, { useRef, useEffect, useState } from 'react';
import CodeEditor, { SupportedLanguage } from '../../../components/archived/CodeEditor';

// Export interfaces for compatibility
export interface ICUIEditorFile {
  id: string;
  name: string;
  content: string;
  language: SupportedLanguage;
  modified?: boolean;
}

export interface ICUIEnhancedEditorPanelProps {
  className?: string;
  // Add optional props for compatibility but don't implement them in this simple version
  files?: ICUIEditorFile[];
  activeFileId?: string;
  onFileChange?: (fileId: string, content: string) => void;
  onFileAdd?: (file: ICUIEditorFile) => void;
  onFileRemove?: (fileId: string) => void;
  onFileActivate?: (fileId: string) => void;
  onFileClose?: (fileId: string) => void;
  onFileCreate?: () => void;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  autoSave?: boolean;
  autoSaveDelay?: number;
}

const ICUIEnhancedEditorPanel: React.FC<ICUIEnhancedEditorPanelProps> = ({ 
  className = '',
  // Accept props for compatibility but ignore them in this simple version
  files,
  activeFileId,
  onFileChange,
  onFileAdd,
  onFileRemove,
  onFileActivate,
  onFileClose,
  onFileCreate,
  onFileSave,
  onFileRun,
  autoSave,
  autoSaveDelay,
  ...props 
}) => {
  const [content, setContent] = useState<string>(`// ICUIEditorPanel initialized!
// This is a minimal code editor implementation

function helloWorld() {
  console.log("Hello from ICUI Editor!");
  return "Hello World!";
}

helloWorld();`);
  const [isModified, setIsModified] = useState(false);
  const [language, setLanguage] = useState<SupportedLanguage>('javascript');
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

  // Handle content changes
  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setIsModified(true);
  };

  // Handle save action
  const handleSave = () => {
    setIsModified(false);
    console.log('File saved:', content);
  };

  // Handle run code action
  const handleRunCode = () => {
    try {
      // Simple code execution for demonstration
      if (language === 'javascript') {
        const result = eval(content);
        console.log('Code execution result:', result);
      }
    } catch (error) {
      console.error('Code execution error:', error);
    }
  };

  return (
    <div className="flex flex-col h-full w-full" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium" style={{ color: 'var(--icui-text-primary)' }}>
            {language?.toUpperCase() || 'PLAIN TEXT'}
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className="text-xs px-2 py-1 rounded border"
            style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)', borderColor: 'var(--icui-border-subtle)' }}
          >
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
            <option value="json">JSON</option>
            <option value="md">Markdown</option>
          </select>
        </div>
        <div className="flex items-center space-x-2">
          <button
            className="px-2 py-1 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-success)', color: 'var(--icui-text-primary)' }}
            onClick={handleSave}
            disabled={!isModified}
          >
            Save
          </button>
          <button
            className="px-2 py-1 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}
            onClick={handleRunCode}
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 min-h-0 overflow-hidden" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
        <div style={{ height: '100%', backgroundColor: 'var(--icui-bg-primary)' }}>
          <CodeEditor
            code={content}
            language={language}
            onCodeChange={handleContentChange}
            theme={isDarkTheme ? 'dark' : 'light'}
          />
        </div>
      </div>

      {/* Status Bar */}
      <div className="px-3 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>Line 1, Column 1</span>
        <span>Ctrl+S to save • Ctrl+Enter to run {isModified && '• Modified'}</span>
      </div>
    </div>
  );
};

export { ICUIEnhancedEditorPanel };
export default ICUIEnhancedEditorPanel;
