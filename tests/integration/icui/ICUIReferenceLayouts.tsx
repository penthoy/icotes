/**
 * ICUI Reference Layout Implementations
 * Step 4.7 - Create reference layout implementations
 */

import React, { useState } from 'react';
import ICUITerminalPanel from '../../../src/icui/components/panels/ICUITerminalPanel';
import ICUIEditorPanel from '../../../src/icui/components/panels/ICUIEditorPanel';
import ICUIExplorerPanel from '../../../src/icui/components/panels/ICUIExplorerPanel';
import ICUIChatPanel from '../../../src/icui/components/panels/ICUIChatPanel';

interface ICUIReferenceLayoutsProps {
  className?: string;
}

type LayoutType = 'top-bottom' | 'left-middle-right' | 'h-layout' | 'ide-classic';

/**
 * Reference Layout Implementations Component
 * Demonstrates different layout presets using minimal panels
 */
export const ICUIReferenceLayouts: React.FC<ICUIReferenceLayoutsProps> = ({ className = '' }) => {
  const [currentLayout, setCurrentLayout] = useState<LayoutType>('ide-classic');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  
  // Apply theme to document root on mount and theme change
  React.useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  // Toggle theme
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Render layout based on current selection
  const renderLayout = () => {
    switch (currentLayout) {
      case 'top-bottom':
        return (
          <div className="h-full grid grid-rows-2 gap-1">
            {/* Top - Editor */}
            <div className="bg-gray-800 rounded">
              <ICUIEditorPanel className="h-full" />
            </div>
            {/* Bottom - Terminal */}
            <div className="bg-gray-800 rounded">
              <ICUITerminalPanel className="h-full" />
            </div>
          </div>
        );

      case 'left-middle-right':
        return (
          <div className="h-full grid grid-cols-3 gap-1">
            {/* Left - Explorer */}
            <div className="bg-gray-800 rounded">
              <ICUIExplorerPanel className="h-full" />
            </div>
            {/* Middle - Editor */}
            <div className="bg-gray-800 rounded">
              <ICUIEditorPanel className="h-full" />
            </div>
            {/* Right - Chat */}
            <div className="bg-gray-800 rounded">
              <ICUIChatPanel className="h-full" />
            </div>
          </div>
        );

      case 'h-layout':
        return (
          <div className="h-full grid grid-cols-3 gap-1">
            {/* Left - Explorer */}
            <div className="bg-gray-800 rounded">
              <ICUIExplorerPanel className="h-full" />
            </div>
            {/* Middle - Split top/bottom (H shape) */}
            <div className="grid grid-rows-2 gap-1">
              {/* Top middle - Editor */}
              <div className="bg-gray-800 rounded">
                <ICUIEditorPanel className="h-full" />
              </div>
              {/* Bottom middle - Terminal */}
              <div className="bg-gray-800 rounded">
                <ICUITerminalPanel className="h-full" />
              </div>
            </div>
            {/* Right - Chat */}
            <div className="bg-gray-800 rounded">
              <ICUIChatPanel className="h-full" />
            </div>
          </div>
        );

      case 'ide-classic':
      default:
        return (
          <div className="h-full grid grid-cols-4 grid-rows-3 gap-1">
            {/* Left - Explorer (spans full height) */}
            <div className="row-span-3 bg-gray-800 rounded">
              <ICUIExplorerPanel className="h-full" />
            </div>
            {/* Center top - Editor (spans 2 columns and 2 rows) */}
            <div className="col-span-2 row-span-2 bg-gray-800 rounded">
              <ICUIEditorPanel className="h-full" />
            </div>
            {/* Right - Chat (spans full height) */}
            <div className="row-span-3 bg-gray-800 rounded">
              <ICUIChatPanel className="h-full" />
            </div>
            {/* Bottom center - Terminal (spans 2 columns) */}
            <div className="col-span-2 bg-gray-800 rounded">
              <ICUITerminalPanel className="h-full" />
            </div>
          </div>
        );
    }
  };

  return (
    <div className={`icui-reference-layouts min-h-screen ${theme} ${className}`}>
      {/* Header */}
      <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">ICUI Reference Layout Implementations</h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm">Layout:</label>
            <select
              value={currentLayout}
              onChange={(e) => setCurrentLayout(e.target.value as LayoutType)}
              className="px-3 py-1 bg-gray-700 text-white rounded border border-gray-600"
            >
              <option value="ide-classic">IDE Classic</option>
              <option value="top-bottom">Top/Bottom (Editor/Terminal)</option>
              <option value="left-middle-right">Left/Middle/Right</option>
              <option value="h-layout">H Layout (Split Middle)</option>
            </select>
          </div>
          <button 
            onClick={toggleTheme}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {theme === 'light' ? '🌙' : '☀️'} {theme === 'light' ? 'Dark' : 'Light'}
          </button>
        </div>
      </div>

      {/* Main layout */}
      <div className="h-[calc(100vh-4rem)] p-1 bg-gray-900">
        {renderLayout()}
      </div>

      {/* Debug info */}
      <div className="bg-gray-100 dark:bg-gray-800 p-2 text-xs">
        <strong>Layout Info:</strong> Current: {currentLayout} | All panels loaded successfully
      </div>
    </div>
  );
};

export default ICUIReferenceLayouts;
