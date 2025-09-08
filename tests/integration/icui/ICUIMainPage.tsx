/**
 * ICUI Main Page Reference Implementation
 * Step 4.8 - Create a reference implementation for the main page
 * Includes all functionality from current home page but with ICUI framework
 */

import React, { useState, useEffect } from 'react';
import ICUITerminalPanel from '../../../src/icui/components/archived/ICUITerminalPanel_deprecate';
import ICUIEditorPanel from '../../../src/icui/components/archived/ICUIEditorPanel_deprecate';
import ICUIExplorerPanel from '../../../src/icui/components/archived/ICUIExplorerPanel_deprecate';
import ICUIChatPanel from '../../../src/icui/components/archived/ICUIChatPanel_deprecate';

interface ICUIMainPageProps {
  className?: string;
}

type LayoutPreset = 'coding' | 'debugging' | 'collaboration' | 'presentation';

/**
 * ICUI Main Page Reference Implementation
 * Demonstrates a complete IDE-like interface using ICUI panels
 */
export const ICUIMainPage: React.FC<ICUIMainPageProps> = ({ className = '' }) => {
  const [currentPreset, setCurrentPreset] = useState<LayoutPreset>('coding');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [terminalCollapsed, setTerminalCollapsed] = useState(false);
  
  // Apply theme to document root on mount and theme change
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  // Toggle theme
  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Layout configurations
  const getLayoutConfig = () => {
    const sidebarWidth = sidebarCollapsed ? 'w-12' : 'w-64';
    const terminalHeight = terminalCollapsed ? 'h-8' : 'h-48';
    
    switch (currentPreset) {
      case 'coding':
        return {
          showExplorer: true,
          showChat: false,
          terminalPosition: 'bottom' as const,
          layout: 'classic' as const
        };
      case 'debugging':
        return {
          showExplorer: true,
          showChat: false,
          terminalPosition: 'bottom' as const,
          layout: 'debug' as const
        };
      case 'collaboration':
        return {
          showExplorer: true,
          showChat: true,
          terminalPosition: 'bottom' as const,
          layout: 'collaborative' as const
        };
      case 'presentation':
        return {
          showExplorer: false,
          showChat: false,
          terminalPosition: 'hidden' as const,
          layout: 'minimal' as const
        };
      default:
        return {
          showExplorer: true,
          showChat: false,
          terminalPosition: 'bottom' as const,
          layout: 'classic' as const
        };
    }
  };

  const config = getLayoutConfig();

  // Render main layout based on configuration
  const renderMainLayout = () => {
    if (config.layout === 'minimal') {
      return (
        <div className="h-full">
          <ICUIEditorPanel className="h-full" />
        </div>
      );
    }

    if (config.layout === 'collaborative') {
      return (
        <div className="h-full grid grid-cols-4 gap-1">
          {/* Explorer */}
          <div className={`bg-gray-800 rounded transition-all duration-300 ${sidebarCollapsed ? 'col-span-0 hidden' : 'col-span-1'}`}>
            <ICUIExplorerPanel className="h-full" />
          </div>
          {/* Editor */}
          <div className={`bg-gray-800 rounded ${sidebarCollapsed ? 'col-span-3' : 'col-span-2'}`}>
            <div className={`h-full ${terminalCollapsed ? '' : 'grid grid-rows-[1fr,auto]'} gap-1`}>
              <div className="bg-gray-800 rounded">
                <ICUIEditorPanel className="h-full" />
              </div>
              {!terminalCollapsed && (
                <div className="bg-gray-800 rounded h-48">
                  <ICUITerminalPanel className="h-full" />
                </div>
              )}
            </div>
          </div>
          {/* Chat */}
          <div className="bg-gray-800 rounded">
            <ICUIChatPanel className="h-full" />
          </div>
        </div>
      );
    }

    // Default classic layout
    return (
      <div className="h-full flex">
        {/* Sidebar - Explorer */}
        {config.showExplorer && (
          <div className={`bg-gray-800 transition-all duration-300 ${sidebarCollapsed ? 'w-12' : 'w-64'}`}>
            <ICUIExplorerPanel className="h-full" />
          </div>
        )}
        
        {/* Main content area */}
        <div className="flex-1 flex flex-col">
          {/* Editor area */}
          <div className={`flex-1 bg-gray-800 ${config.showExplorer ? 'ml-1' : ''}`}>
            <ICUIEditorPanel className="h-full" />
          </div>
          
          {/* Terminal area */}
          {config.terminalPosition === 'bottom' && (
            <div className={`bg-gray-800 mt-1 transition-all duration-300 ${terminalCollapsed ? 'h-8' : 'h-48'}`}>
              <ICUITerminalPanel className="h-full" />
            </div>
          )}
        </div>
        
        {/* Chat sidebar */}
        {config.showChat && (
          <div className="w-80 bg-gray-800 ml-1">
            <ICUIChatPanel className="h-full" />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`icui-main-page min-h-screen ${theme} ${className}`}>
      {/* Header/Menubar */}
      <div className="bg-gray-800 text-white border-b border-gray-700">
        {/* Top menu bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-bold">ICUI Code Editor</h1>
            <nav className="flex items-center space-x-4 text-sm">
              <button className="hover:text-blue-400">File</button>
              <button className="hover:text-blue-400">Edit</button>
              <button className="hover:text-blue-400">View</button>
              <button className="hover:text-blue-400">Run</button>
              <button className="hover:text-blue-400">Terminal</button>
              <button className="hover:text-blue-400">Help</button>
            </nav>
          </div>
          
          <div className="flex items-center space-x-2">
            <select
              value={currentPreset}
              onChange={(e) => setCurrentPreset(e.target.value as LayoutPreset)}
              className="px-2 py-1 bg-gray-700 text-white rounded text-xs border border-gray-600"
            >
              <option value="coding">Coding</option>
              <option value="debugging">Debugging</option>
              <option value="collaboration">Collaboration</option>
              <option value="presentation">Presentation</option>
            </select>
            
            <button 
              onClick={toggleTheme}
              className="px-2 py-1 bg-gray-700 text-white rounded hover:bg-gray-600 text-xs"
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
          </div>
        </div>
        
        {/* Secondary toolbar */}
        <div className="flex items-center justify-between px-4 py-1 text-xs">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="hover:text-blue-400"
            >
              {sidebarCollapsed ? '📁 Show Explorer' : '📁 Hide Explorer'}
            </button>
            <button
              onClick={() => setTerminalCollapsed(!terminalCollapsed)}
              className="hover:text-blue-400"
            >
              {terminalCollapsed ? '💻 Show Terminal' : '💻 Hide Terminal'}
            </button>
          </div>
          
          <div className="text-gray-400">
            Layout: {currentPreset} | Theme: {theme}
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="h-[calc(100vh-4rem)] p-1 bg-gray-900">
        {renderMainLayout()}
      </div>

      {/* Status bar */}
      <div className="bg-gray-800 text-white px-4 py-1 text-xs border-t border-gray-700 flex justify-between">
        <div className="flex items-center space-x-4">
          <span>Ready</span>
          <span>Ln 1, Col 1</span>
          <span>Spaces: 2</span>
          <span>UTF-8</span>
        </div>
        <div className="flex items-center space-x-4">
          <span>ICUI Framework</span>
          <span>Powered by React + Vite</span>
        </div>
      </div>
    </div>
  );
};

export default ICUIMainPage;
