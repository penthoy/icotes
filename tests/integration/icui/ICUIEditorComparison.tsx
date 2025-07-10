/**
 * ICUI Editor Comparison Page
 * Shows side-by-side comparison of ICUI-styled vs standalone editor
 * to help debug highlighting and styling issues
 */

import React, { useState, useEffect } from 'react';
import ICUIEditorPanelFromScratch from '../../../src/icui/components/panels/ICUIEditorPanelFromScratch';
import ICUIEnhancedEditorPanel from '../../../src/icui/components/panels/ICUIEnhancedEditorPanelOld';
import '../../../src/icui/styles/themes/icui-themes.css';

const ICUIEditorComparison: React.FC = () => {
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

  return (
    <div className="h-screen w-full" style={{ backgroundColor: 'var(--icui-bg-primary, #1e1e1e)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary, #2d2d2d)', borderBottomColor: 'var(--icui-border-subtle, #3e3e3e)' }}>
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-semibold" style={{ color: 'var(--icui-text-primary, #d4d4d4)' }}>
            ICUI Editor Comparison
          </h1>
          <span className="text-sm px-2 py-1 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary, #3e3e3e)', color: 'var(--icui-text-muted, #969696)' }}>
            Side-by-Side Debugging
          </span>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={theme}
            onChange={(e) => handleThemeChange(e.target.value)}
            className="px-3 py-1 text-sm rounded border"
            style={{ backgroundColor: 'var(--icui-bg-primary, #1e1e1e)', color: 'var(--icui-text-primary, #d4d4d4)', borderColor: 'var(--icui-border-subtle, #3e3e3e)' }}
          >
            <option value="icui-theme-github-dark">GitHub Dark</option>
            <option value="icui-theme-github-light">GitHub Light</option>
            <option value="icui-theme-monokai">Monokai</option>
            <option value="icui-theme-one-dark">One Dark</option>
            <option value="icui-theme-vscode-light">VS Code Light</option>
          </select>
        </div>
      </div>

      {/* Comparison Layout */}
      <div className="flex h-full" style={{ height: 'calc(100vh - 60px)' }}>
        {/* Left Side - ICUI Styled Editor */}
        <div className="flex-1 border-r" style={{ borderRightColor: 'var(--icui-border-subtle, #3e3e3e)' }}>
          <div className="h-full flex flex-col">
            <div className="px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary, #2d2d2d)', borderBottomColor: 'var(--icui-border-subtle, #3e3e3e)' }}>
              <h2 className="text-lg font-medium" style={{ color: 'var(--icui-text-primary, #d4d4d4)' }}>
                ICUI Styled Editor
              </h2>
              <p className="text-sm" style={{ color: 'var(--icui-text-muted, #969696)' }}>
                Uses ICUI CSS variables - may have highlighting issues
              </p>
            </div>
            <div className="flex-1">
              <ICUIEnhancedEditorPanel />
            </div>
          </div>
        </div>

        {/* Right Side - Standalone Editor */}
        <div className="flex-1">
          <div className="h-full flex flex-col">
            <div className="px-4 py-2 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary, #2d2d2d)', borderBottomColor: 'var(--icui-border-subtle, #3e3e3e)' }}>
              <h2 className="text-lg font-medium" style={{ color: 'var(--icui-text-primary, #d4d4d4)' }}>
                Standalone Editor
              </h2>
              <p className="text-sm" style={{ color: 'var(--icui-text-muted, #969696)' }}>
                Independent styles - should work correctly
              </p>
            </div>
            <div className="flex-1">
              <ICUIEditorPanelFromScratch />
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-1 border-t text-xs flex justify-between" style={{ backgroundColor: 'var(--icui-bg-secondary, #2d2d2d)', borderTopColor: 'var(--icui-border-subtle, #3e3e3e)', color: 'var(--icui-text-muted, #969696)' }}>
        <span>Compare ICUI vs Standalone Editor Implementations</span>
        <span>Use this to debug highlighting and styling issues</span>
      </div>
      
      {/* Navigation */}
      <div className="px-4 py-2 border-t" style={{ backgroundColor: 'var(--icui-bg-secondary, #2d2d2d)', borderTopColor: 'var(--icui-border-subtle, #3e3e3e)' }}>
        <div className="flex justify-between items-center">
          <a 
            href="/icui-test4.9" 
            className="px-4 py-2 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-bg-tertiary, #3e3e3e)', color: 'var(--icui-text-primary, #d4d4d4)' }}
          >
            ← Test 4.9
          </a>
          <div className="text-xs" style={{ color: 'var(--icui-text-muted, #969696)' }}>
            Editor Comparison Tool
          </div>
          <a 
            href="/icui-enhanced" 
            className="px-4 py-2 text-xs rounded hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--icui-bg-tertiary, #3e3e3e)', color: 'var(--icui-text-primary, #d4d4d4)' }}
          >
            Enhanced Test →
          </a>
        </div>
      </div>
    </div>
  );
};

export default ICUIEditorComparison; 