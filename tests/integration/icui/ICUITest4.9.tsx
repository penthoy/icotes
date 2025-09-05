/**
 * ICUI Test 4.9 - From Scratch Editor Implementation
 * Test page for the minimal Python editor built from scratch
 */

import React, { useState, useEffect } from 'react';
import ICUILayout from '../../../src/icui/components/ICUILayout';
import ICUIEditorPanel from '../../../src/icui/components/archived/ICUIEditorPanel_deprecate';
import '../../../src/icui/styles/themes/icui-themes.css';

const ICUITest49: React.FC = () => {
  const [theme, setTheme] = useState('icui-theme-github-dark');

  // Initialize theme on mount
  useEffect(() => {
    const htmlElement = document.documentElement;
    htmlElement.classList.add(theme);
    
    return () => {
      // Cleanup on unmount
      htmlElement.classList.remove(
        'icui-theme-github-dark',
        'icui-theme-github-light',
        'icui-theme-monokai',
        'icui-theme-one-dark',
        'icui-theme-vscode-light'
      );
    };
  }, []);

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    // Remove all theme classes
    const htmlElement = document.documentElement;
    htmlElement.classList.remove(
      'icui-theme-github-dark',
      'icui-theme-github-light',
      'icui-theme-monokai',
      'icui-theme-one-dark',
      'icui-theme-vscode-light'
    );
    // Add new theme class
    htmlElement.classList.add(newTheme);
  };

  // Initial panels setup - single editor panel
  const panels = [
    {
      id: 'editor-from-scratch',
      type: 'editor-from-scratch',
      title: 'Python Editor (From Scratch)',
      content: <ICUIEditorPanel />,
      closable: true,
    },
  ];

  // Layout configuration for the editor panel
  const layout = {
    areas: {
      center: { 
        id: 'center', 
        name: 'Main Area', 
        panelIds: ['editor-from-scratch'],
        activePanelId: 'editor-from-scratch',
        size: 100,
        visible: true
      },
    },
    splitConfig: {
      mainVerticalSplit: 100,
      mainHorizontalSplit: 100,
    }
  };

  return (
    <div className="h-screen w-full" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border-subtle)' }}>
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold" style={{ color: 'var(--icui-text-primary)' }}>
            ICUI Test 4.9 - From Scratch Editor
          </h1>
          <span className="text-sm px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-muted)' }}>
            Python Editor Implementation
          </span>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={theme}
            onChange={(e) => handleThemeChange(e.target.value)}
            className="px-3 py-1 text-sm rounded border"
            style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)', borderColor: 'var(--icui-border-subtle)' }}
          >
            <option value="icui-theme-github-dark">GitHub Dark</option>
            <option value="icui-theme-github-light">GitHub Light</option>
            <option value="icui-theme-monokai">Monokai</option>
            <option value="icui-theme-one-dark">One Dark</option>
            <option value="icui-theme-vscode-light">VS Code Light</option>
          </select>
        </div>
      </div>

      {/* Main Layout - Simplified for testing */}
      <div className="flex-1 h-full" style={{ height: 'calc(100vh - 60px)' }}>
        <div className="h-full w-full" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
          <ICUIEditorPanel />
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-muted)' }}>
        <span>ICUI Test 4.9 - From Scratch Editor Implementation</span>
        <span>Testing minimal Python editor without CodeEditor.tsx dependencies</span>
      </div>
      
      {/* Navigation */}
      <div className="px-4 py-2 border-t" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderTopColor: 'var(--icui-border-subtle)' }}>
        <div className="flex justify-between items-center">
          <a 
            href="/icui-test4.5" 
            className="px-4 py-2 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
          >
            ← Test 4.5
          </a>
          <div className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>
            Step 4.9 - From Scratch Editor Implementation
          </div>
          <div className="flex space-x-2">
            <a 
              href="/icui-editor-comparison" 
              className="px-4 py-2 text-xs rounded hover:opacity-80 transition-opacity"
              style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }}
            >
              Compare →
            </a>
            <a 
              href="/icui-main" 
              className="px-4 py-2 text-xs rounded hover:opacity-80 transition-opacity"
              style={{ backgroundColor: 'var(--icui-bg-tertiary)', color: 'var(--icui-text-primary)' }}
            >
              ICUI Main →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ICUITest49; 