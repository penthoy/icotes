/**
 * ICUI Framework Test Component - Phase 4.5 (Minimal Panel Implementations)
 * Demonstrates minimal panel implementations and chat panel integration
 */

import React, { useState } from 'react';
import ICUITerminalPanel from '../../../src/icui/components/panels/ICUITerminalPanel';
import ICUIEditorPanel from '../../../src/icui/components/panels/ICUIEditorPanel';
import ICUIExplorerPanel from '../../../src/icui/components/panels/ICUIExplorerPanel';
import ICUIChatPanel from '../../../src/icui/components/panels/ICUIChatPanel';

interface ICUITest45Props {
  className?: string;
}

/**
 * Test component for ICUI Framework Phase 4.5
 * Shows minimal panel implementations including the new chat panel
 */
export const ICUITest45: React.FC<ICUITest45Props> = ({ className = '' }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  
  // Apply theme to document root on mount and theme change
  React.useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  // Theme toggle function
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div className={`icui-test45 min-h-screen ${theme} ${className}`}>
      {/* Header */}
      <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">ICUI Test 4.5 - Minimal Panel Implementations</h1>
        <div className="flex items-center space-x-4">
          <button 
            onClick={toggleTheme}
            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            {theme === 'light' ? '🌙' : '☀️'} {theme === 'light' ? 'Dark' : 'Light'}
          </button>
        </div>
      </div>

      {/* Main layout - Simple grid layout for demonstration */}
      <div className="h-[calc(100vh-4rem)] grid grid-cols-3 grid-rows-2 gap-1 p-1 bg-gray-900">
        {/* Left area - Explorer */}
        <div className="row-span-2 bg-gray-800 rounded">
          <ICUIExplorerPanel className="h-full" />
        </div>

        {/* Center top - Editor */}
        <div className="bg-gray-800 rounded">
          <ICUIEditorPanel className="h-full" />
        </div>

        {/* Right area - Chat */}
        <div className="row-span-2 bg-gray-800 rounded">
          <ICUIChatPanel className="h-full" />
        </div>

        {/* Center bottom - Terminal */}
        <div className="bg-gray-800 rounded">
          <ICUITerminalPanel className="h-full" />
        </div>
      </div>

      {/* Debug info */}
      <div className="bg-gray-100 dark:bg-gray-800 p-2 text-xs">
        <strong>Debug Info:</strong> All minimal panels loaded successfully
      </div>
    </div>
  );
};

export default ICUITest45;
