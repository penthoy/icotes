/**
 * Layout Component
 * Extends ICUI base header and footer classes to create a complete application layout
 * Provides enhanced functionality for the icotes editor
 */

import React, { useState, useCallback, useEffect } from 'react';
import { ICUIBaseHeader, ICUIBaseFooter } from '../icui';
import type { ICUIBaseHeaderProps, ICUIBaseFooterProps } from '../icui';

export interface LayoutProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  // Header configuration
  headerConfig?: Partial<ICUIBaseHeaderProps> & {
    showLogo?: boolean;
    showMenuBar?: boolean;
    showThemeSelector?: boolean;
    customMenuItems?: Array<{
      menuId: string;
      items: Array<{
        id: string;
        label: string;
        onClick?: () => void;
        keyboard?: string;
      }>;
    }>;
  };
  // Footer configuration  
  footerConfig?: Partial<ICUIBaseFooterProps> & {
    showConnectionStatus?: boolean;
    showFileStats?: boolean;
    showThemeInfo?: boolean;
    customStatusItems?: Array<{
      id: string;
      label: string;
      value: string | number;
      icon?: string;
      color?: string;
      onClick?: () => void;
    }>;
  };
  // Application state
  appState?: {
    currentTheme?: string;
    availableThemes?: Array<{ id: string; name: string; class: string }>;
    files?: Array<{ id: string; name: string; modified: boolean }>;
    connectionStatus?: 'connected' | 'disconnected' | 'connecting' | 'error';
  };
  // Event handlers
  onThemeChange?: (themeId: string) => void;
  onLayoutChange?: (layoutId: string) => void;
  onMenuItemClick?: (menuId: string, itemId: string) => void;
  onFileAction?: (action: string, fileId?: string) => void;
}

// Default theme options
const DEFAULT_THEMES = [
  { id: 'github-dark', name: 'GitHub Dark', class: 'icui-theme-github-dark' },
  { id: 'monokai', name: 'Monokai', class: 'icui-theme-monokai' },
  { id: 'one-dark', name: 'One Dark', class: 'icui-theme-one-dark' },
  { id: 'github-light', name: 'GitHub Light', class: 'icui-theme-github-light' },
  { id: 'vscode-light', name: 'VS Code Light', class: 'icui-theme-vscode-light' },
];

/**
 * Layout Component
 * Complete application layout with enhanced header and footer functionality
 */
export const Layout: React.FC<LayoutProps> = ({
  className = '',
  style,
  children,
  headerConfig = {},
  footerConfig = {},
  appState = {},
  onThemeChange,
  onLayoutChange,
  onMenuItemClick,
  onFileAction,
}) => {
  // Merge default configuration with provided config
  const {
    showLogo = true,
    showMenuBar = true,
    showThemeSelector = true,
    customMenuItems = [],
    ...headerProps
  } = headerConfig;

  const {
    showConnectionStatus = true,
    showFileStats = true,
    showThemeInfo = true,
    customStatusItems = [],
    ...footerProps
  } = footerConfig;

  // Get app state with defaults
  const {
    currentTheme = 'github-dark',
    availableThemes = DEFAULT_THEMES,
    files = [],
    connectionStatus = 'connected',
  } = appState;

  // Handle enhanced menu item clicks
  const handleMenuItemClick = useCallback((menuId: string, itemId: string) => {
    // Handle built-in menu actions
    switch (menuId) {
      case 'file':
        switch (itemId) {
          case 'new':
            onFileAction?.('new');
            break;
          case 'open':
            onFileAction?.('open');
            break;
          case 'save':
            onFileAction?.('save');
            break;
          case 'save-as':
            onFileAction?.('save-as');
            break;
          case 'exit':
            onFileAction?.('exit');
            break;
        }
        break;
      case 'layout':
        switch (itemId) {
          case 'h-layout':
            onLayoutChange?.('h-layout');
            break;
          case 'ide-layout':
            onLayoutChange?.('ide-layout');
            break;
          case 'reset-layout':
            onLayoutChange?.('reset');
            break;
        }
        break;
    }

    // Handle custom menu items
    const customMenu = customMenuItems.find(menu => menu.menuId === menuId);
    if (customMenu) {
      const customItem = customMenu.items.find(item => item.id === itemId);
      if (customItem?.onClick) {
        customItem.onClick();
      }
    }

    // Notify parent
    onMenuItemClick?.(menuId, itemId);
  }, [customMenuItems, onMenuItemClick, onFileAction, onLayoutChange]);

  // Layout actions are now in the menu system, no longer needed as buttons
  const layoutActions: Array<{
    id: string;
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'warning';
  }> = [];

  // Generate status items
  const statusItems = [
    ...customStatusItems,
    ...(showFileStats ? [
      {
        id: 'file-count',
        label: 'Files',
        value: files.length,
        icon: '📄',
      },
      {
        id: 'modified-count',
        label: 'Modified',
        value: files.filter(f => f.modified).length,
        icon: '✏️',
        color: files.filter(f => f.modified).length > 0 ? 'var(--icui-warning)' : undefined,
      },
    ] : []),
    ...(showThemeInfo ? [
      {
        id: 'theme-info',
        label: 'Theme',
        value: availableThemes.find(t => t.id === currentTheme)?.name || 'Unknown',
        icon: '🎨',
      },
    ] : []),
  ];

  // Generate header configuration
  const headerConfiguration: ICUIBaseHeaderProps = {
    ...headerProps,
    logo: showLogo ? {
      src: '/logo.png',
      alt: 'icotes',
      className: '',
    } : undefined,
    currentTheme: showThemeSelector ? currentTheme : undefined,
    availableThemes: showThemeSelector ? availableThemes : [],
    onThemeChange: showThemeSelector ? onThemeChange : undefined,
    layoutActions,
    onMenuItemClick: handleMenuItemClick,
  };

  // Generate footer configuration
  const footerConfiguration: ICUIBaseFooterProps = {
    ...footerProps,
    statusItems,
    connectionStatus: showConnectionStatus ? connectionStatus : undefined,
    statusText: 'Ready',
  };

  return (
    <div 
      className={`layout-container flex flex-col ${className}`}
      style={{ 
        height: '100vh', 
        minHeight: '100vh', 
        maxHeight: '100vh',
        ...style,
      }}
    >
      {/* Enhanced Header */}
      <ICUIBaseHeader {...headerConfiguration} />

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 max-h-full overflow-hidden">
        {children}
      </div>

      {/* Enhanced Footer */}
      <ICUIBaseFooter {...footerConfiguration} />
    </div>
  );
};

export default Layout; 