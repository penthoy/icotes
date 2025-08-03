/**
 * ICUI Editor Panel - Simple Implementation
 * A basic code editor using native textarea element
 * No CodeMirror dependency - built from scratch
 */

import React, { useState, useRef } from 'react';

// Export interface for compatibility with enhanced version
export interface ICUIEditorFile {
  id: string;
  name: string;
  language: string;
  content: string;
  modified: boolean;
}

interface ICUIEditorPanelProps {
  className?: string;
  // Accept enhanced props for compatibility but ignore them
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

const ICUIEditorPanel: React.FC<ICUIEditorPanelProps> = ({ className = '' }) => {
  const [content, setContent] = useState<string>(`// ICUI Editor Panel - Simple Implementation
// No CodeMirror - just a plain textarea

function example() {
  return "This is a basic implementation";
}

example();`);

  const [isModified, setIsModified] = useState(false);
  const [language, setLanguage] = useState('javascript');
  const [lineNumbers, setLineNumbers] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Calculate line numbers
  const lines = content.split('\n');
  const lineCount = lines.length;

  // Handle content change
  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setIsModified(true);
  };

  // Handle save
  const handleSave = () => {
    setIsModified(false);
  };

  // Handle run code
  const handleRun = () => {
    try {
      if (language === 'javascript') {
        // Simple evaluation for demo purposes
        eval(content);
      }
    } catch (error) {
      console.error('Code execution error:', error);
    }
  };

  // Handle key shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 's') {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        handleRun();
      }
    }
    
    // Tab handling
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const value = textarea.value;
        
        // Insert tab
        const newValue = value.substring(0, start) + '  ' + value.substring(end);
        setContent(newValue);
        setIsModified(true);
        
        // Move cursor after tab
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        }, 0);
      }
    }
  };

  return (
    <div className={`flex flex-col h-full w-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-300 dark:border-gray-600">
        <div className="flex items-center space-x-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Editor
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-xs px-2 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
            <option value="text">Plain Text</option>
          </select>
          <button
            onClick={() => setLineNumbers(!lineNumbers)}
            className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
          >
            {lineNumbers ? 'Hide' : 'Show'} Lines
          </button>
        </div>
        
        <div className="flex items-center space-x-2">
          {isModified && (
            <span className="text-xs text-orange-600 dark:text-orange-400">
              Modified
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={!isModified}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              isModified 
                ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
            }`}
          >
            Save
          </button>
          <button
            onClick={handleRun}
            className="px-3 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded transition-colors"
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Line Numbers */}
        {lineNumbers && (
          <div className="flex-shrink-0 bg-gray-50 dark:bg-gray-800 border-r border-gray-300 dark:border-gray-600 px-3 py-2">
            <div className="text-xs text-gray-500 dark:text-gray-400 font-mono leading-6">
              {Array.from({ length: lineCount }, (_, i) => (
                <div key={i + 1} className="text-right">
                  {i + 1}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Text Area */}
        <div className="flex-1 min-w-0">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleContentChange}
            onKeyDown={handleKeyDown}
            className="w-full h-full p-2 font-mono text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border-none resize-none focus:outline-none leading-6"
            placeholder="Start typing your code here..."
            spellCheck={false}
            style={{ 
              tabSize: 2,
              minHeight: '100%',
              outline: 'none',
              border: 'none',
            }}
          />
        </div>
      </div>

      {/* Status Bar */}
      <div className="flex items-center justify-between px-4 py-1 bg-gray-50 dark:bg-gray-800 border-t border-gray-300 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-400">
        <div className="flex items-center space-x-4">
          <span>Lines: {lineCount}</span>
          <span>Characters: {content.length}</span>
          <span>Language: {language}</span>
        </div>
        <div className="flex items-center space-x-2">
          <span>Ctrl+S to save</span>
          <span>•</span>
          <span>Ctrl+Enter to run</span>
          <span>•</span>
          <span>Tab to indent</span>
        </div>
      </div>
    </div>
  );
};

export default ICUIEditorPanel; 