/**
 * ICUIBaseHeader: Single source of truth for top menus in Home.
 * Provides logo slot, menu system, theme selector, and optional layout actions.
 */

import React, { useState, useCallback } from 'react';
import { Button } from './ui/button';

export interface ICUIBaseHeaderProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  // Logo props
  logo?: {
    src: string;
    alt: string;
    className?: string;
  };
  // Menu props
  onMenuItemClick?: (menuId: string, itemId: string) => void;
  // Theme props
  currentTheme?: string;
  availableThemes?: Array<{ id: string; name: string; class: string }>;
  onThemeChange?: (themeId: string) => void;
  // Layout props
  layoutActions?: Array<{
    id: string;
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'warning';
  }>;
}

export interface ICUIMenuProps {
  id: string;
  label: string;
  items: Array<{
    id: string;
    label: string;
    onClick?: () => void;
    separator?: boolean;
    disabled?: boolean;
  }>;
}

export interface ICUIBaseHeaderState {
  activeMenu?: string;
  isMenuOpen: boolean;
}

/**
 * Base Header Component
 * Provides common header functionality with menu system, theme switcher, and layout controls
 */
export const ICUIBaseHeader: React.FC<ICUIBaseHeaderProps> = ({
  className = '',
  style,
  children,
  logo,
  onMenuItemClick,
  currentTheme,
  availableThemes = [],
  onThemeChange,
  layoutActions = [],
}) => {
  const [menuState, setMenuState] = useState<ICUIBaseHeaderState>({
    isMenuOpen: false,
  });

  // Handle menu toggle
  const handleMenuToggle = useCallback((menuId: string) => {
    setMenuState(prev => ({
      ...prev,
      activeMenu: prev.activeMenu === menuId ? undefined : menuId,
      isMenuOpen: prev.activeMenu !== menuId,
    }));
  }, []);

  // Handle menu item click
  const handleMenuItemClick = useCallback((menuId: string, itemId: string) => {
    setMenuState(prev => ({
      ...prev,
      activeMenu: undefined,
      isMenuOpen: false,
    }));
    onMenuItemClick?.(menuId, itemId);
  }, [onMenuItemClick]);

  // Close menu when clicking outside
  const handleMenuClose = useCallback(() => {
    setMenuState(prev => ({
      ...prev,
      activeMenu: undefined,
      isMenuOpen: false,
    }));
  }, []);

  // Default menus
  const defaultMenus: ICUIMenuProps[] = [
    {
      id: 'file',
      label: 'File',
      items: [
        { id: 'new', label: 'New' },
        { id: 'open', label: 'Open...' },
        { id: 'save', label: 'Save' },
        { id: 'save-as', label: 'Save As...' },
        { id: 'separator1', label: '', separator: true },
        { id: 'exit', label: 'Exit' },
      ],
    },
    {
      id: 'layout',
      label: 'Layout',
      items: [
        { id: 'h-layout', label: 'H Layout' },
        { id: 'ide-layout', label: 'IDE Layout' },
        { id: 'separator1', label: '', separator: true },
        { id: 'reset-layout', label: 'Reset Layout' },
      ],
    },
  ];

  // Get current theme info
  const currentThemeInfo = availableThemes.find(t => t.id === currentTheme) || availableThemes[0];

  return (
    <div 
      className={`icui-base-header flex items-center justify-between border-b shrink-0 ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)',
        color: 'var(--icui-text-primary)',
        padding: '3px 16px', // Slightly more padding to accommodate bigger menu buttons
        minHeight: '28px', // Adjusted height for better menu button proportions
        ...style,
      }}
    >
      {/* Left side - Logo and Menus */}
      <div className="flex items-center space-x-2">
        {/* Logo */}
        {logo && (
          <img 
            src={logo.src} 
            alt={logo.alt} 
            className={`h-4 ${logo.className || ''}`} // Ultra-small logo - h-4 for ultra-narrow header
          />
        )}

        {/* Menu Bar */}
        <div className="flex items-center space-x-1">
          {defaultMenus.map(menu => (
            <div key={menu.id} className="relative">
              <button
                onClick={() => handleMenuToggle(menu.id)}
                className="px-3 py-1 text-sm rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                style={{ color: 'var(--icui-text-primary)' }}
              >
                {menu.label}
              </button>
              
              {/* Dropdown Menu */}
              {menuState.activeMenu === menu.id && (
                <>
                  {/* Backdrop */}
                  <div 
                    className="fixed inset-0 z-10"
                    onClick={handleMenuClose}
                  />
                  
                  {/* Menu Items */}
                  <div 
                    className="absolute top-full left-0 z-20 mt-1 min-w-[150px] rounded-md shadow-lg border"
                    style={{
                      backgroundColor: 'var(--icui-bg-primary)',
                      borderColor: 'var(--icui-border)',
                    }}
                  >
                    {menu.items.map(item => (
                      item.separator ? (
                        <div 
                          key={item.id}
                          className="h-px my-1"
                          style={{ backgroundColor: 'var(--icui-border-subtle)' }}
                        />
                      ) : (
                        <button
                          key={item.id}
                          onClick={() => handleMenuItemClick(menu.id, item.id)}
                          disabled={item.disabled}
                          className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          style={{ color: 'var(--icui-text-primary)' }}
                        >
                          {item.label}
                        </button>
                      )
                    ))}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right side - Theme Selector */}
      <div className="flex items-center space-x-1">
        {/* Layout Actions */}
        {layoutActions.map(action => (
          <Button
            key={action.id}
            onClick={action.onClick}
            variant={action.variant === 'primary' ? 'default' : 'outline'}
            size="sm"
            className="px-3 py-1 text-sm"
            style={action.variant === 'warning' ? { backgroundColor: 'var(--icui-warning)' } : {}}
          >
            {action.label}
          </Button>
        ))}

        {/* Theme Selector */}
        {availableThemes.length > 0 && (
          <select
            value={currentTheme}
            onChange={(e) => onThemeChange?.(e.target.value)}
            className="px-2 py-0 text-xs rounded border"
            style={{
              backgroundColor: 'var(--icui-bg-primary)',
              borderColor: 'var(--icui-border)',
              color: 'var(--icui-text-primary)',
            }}
          >
            {availableThemes.map(theme => (
              <option key={theme.id} value={theme.id}>
                {theme.name}
              </option>
            ))}
          </select>
        )}

        {/* Custom content */}
        {children}
      </div>
    </div>
  );
};

export default ICUIBaseHeader; 