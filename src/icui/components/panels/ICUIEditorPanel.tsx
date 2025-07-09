/**
 * ICUI Editor Panel - Reference Implementation
 * A minimal, working code editor panel for the ICUI framework
 * Following the same pattern as ICUITerminalPanel
 */

import React, { useRef, useEffect, useState } from 'react';

interface ICUIEditorPanelProps {
  className?: string;
}

const ICUIEditorPanel: React.FC<ICUIEditorPanelProps> = ({ className = '' }) => {
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const [content, setContent] = useState<string>(`// ICUIEditorPanel initialized!
// This is a minimal code editor implementation

function helloWorld() {
  console.log("Hello from ICUI Editor!");
  return "Hello World!";
}

helloWorld();`);
  const [isModified, setIsModified] = useState(false);
  const [language, setLanguage] = useState('javascript');

  // Handle content changes
  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
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

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      handleRunCode();
    }
  };

  return (
    <div className={`icui-editor-panel h-full flex flex-col bg-black text-white ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium">
            untitled.{language} {isModified ? '●' : ''}
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="text-xs bg-gray-700 text-white border border-gray-600 rounded px-1 py-0.5"
          >
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="python">Python</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
          </select>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleSave}
            disabled={!isModified}
            className="text-xs px-2 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded"
          >
            Save
          </button>
          <button
            onClick={handleRunCode}
            className="text-xs px-2 py-1 bg-green-600 hover:bg-green-700 rounded"
          >
            Run
          </button>
        </div>
      </div>

      {/* Editor area */}
      <div className="flex-1 relative">
        <textarea
          ref={editorRef}
          value={content}
          onChange={handleContentChange}
          onKeyDown={handleKeyDown}
          className="w-full h-full p-3 bg-black text-white font-mono text-sm resize-none border-none outline-none"
          style={{
            fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
            lineHeight: '1.5',
            scrollbarWidth: 'thin',
            scrollbarColor: '#4B5563 #1F2937'
          }}
          placeholder="Start typing your code..."
          spellCheck={false}
        />
      </div>

      {/* Status bar */}
      <div className="px-3 py-1 bg-gray-800 border-t border-gray-700 text-xs text-gray-400 flex justify-between">
        <span>Line 1, Column 1</span>
        <span>Ctrl+S to save • Ctrl+Enter to run</span>
      </div>
    </div>
  );
};

export default ICUIEditorPanel;
