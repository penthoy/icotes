/**
 * ICUI Menu Bar Component
 * 
 * Top menu bar implementation for the ICUI framework with dropdown menus
 * for File, Edit, View, and Layout operations. Includes keyboard shortcut
 * support and menu customization capabilities.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { notificationService } from '../../services/notificationService';

export interface ICUIMenuBarShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
}

export interface ICUIMenuBarItem {
  id: string;
  label: string;
  disabled?: boolean;
  shortcut?: ICUIMenuBarShortcut;
  shortcutDisplay?: string;
  separator?: boolean;
  submenu?: ICUIMenuBarItem[];
  onClick?: () => void;
}

export interface ICUIMenuBarMenu {
  id: string;
  label: string;
  items: ICUIMenuBarItem[];
}

export interface ICUIMenuBarProps {
  menus?: ICUIMenuBarMenu[];
  onMenuItemClick?: (menuId: string, itemId: string) => void;
  className?: string;
  style?: React.CSSProperties;
  showKeyboardShortcuts?: boolean;
  disabled?: boolean;
}

// Default menus for ICUI
const createDefaultMenus = (
  onMenuItemClick?: (menuId: string, itemId: string) => void
): ICUIMenuBarMenu[] => [
  {
    id: 'file',
    label: 'File',
    items: [
      {
        id: 'new',
        label: 'New File',
        shortcut: { key: 'n', ctrlKey: true },
        shortcutDisplay: 'Ctrl+N',
        onClick: () => onMenuItemClick?.('file', 'new')
      },
      {
        id: 'open',
        label: 'Open...',
        shortcut: { key: 'o', ctrlKey: true },
        shortcutDisplay: 'Ctrl+O',
        onClick: () => onMenuItemClick?.('file', 'open')
      },
      { id: 'separator-1', label: '', separator: true },
      {
        id: 'save',
        label: 'Save',
        shortcut: { key: 's', ctrlKey: true },
        shortcutDisplay: 'Ctrl+S',
        onClick: () => onMenuItemClick?.('file', 'save')
      },
      {
        id: 'save-as',
        label: 'Save As...',
        shortcut: { key: 's', ctrlKey: true, shiftKey: true },
        shortcutDisplay: 'Ctrl+Shift+S',
        onClick: () => onMenuItemClick?.('file', 'save-as')
      },
      { id: 'separator-2', label: '', separator: true },
      {
        id: 'settings',
        label: 'Settings',
        onClick: () => onMenuItemClick?.('file', 'settings')
      },
      { id: 'separator-3', label: '', separator: true },
      {
        id: 'close',
        label: 'Close File',
        shortcut: { key: 'w', ctrlKey: true },
        shortcutDisplay: 'Ctrl+W',
        onClick: () => onMenuItemClick?.('file', 'close')
      }
    ]
  },
  {
    id: 'edit',
    label: 'Edit',
    items: [
      {
        id: 'undo',
        label: 'Undo',
        shortcut: { key: 'z', ctrlKey: true },
        shortcutDisplay: 'Ctrl+Z',
        onClick: () => onMenuItemClick?.('edit', 'undo')
      },
      {
        id: 'redo',
        label: 'Redo',
        shortcut: { key: 'y', ctrlKey: true },
        shortcutDisplay: 'Ctrl+Y',
        onClick: () => onMenuItemClick?.('edit', 'redo')
      },
      { id: 'separator-1', label: '', separator: true },
      {
        id: 'cut',
        label: 'Cut',
        shortcut: { key: 'x', ctrlKey: true },
        shortcutDisplay: 'Ctrl+X',
        onClick: () => onMenuItemClick?.('edit', 'cut')
      },
      {
        id: 'copy',
        label: 'Copy',
        shortcut: { key: 'c', ctrlKey: true },
        shortcutDisplay: 'Ctrl+C',
        onClick: () => onMenuItemClick?.('edit', 'copy')
      },
      {
        id: 'paste',
        label: 'Paste',
        shortcut: { key: 'v', ctrlKey: true },
        shortcutDisplay: 'Ctrl+V',
        onClick: () => onMenuItemClick?.('edit', 'paste')
      },
      { id: 'separator-2', label: '', separator: true },
      {
        id: 'select-all',
        label: 'Select All',
        shortcut: { key: 'a', ctrlKey: true },
        shortcutDisplay: 'Ctrl+A',
        onClick: () => onMenuItemClick?.('edit', 'select-all')
      },
      {
        id: 'find',
        label: 'Find',
        shortcut: { key: 'f', ctrlKey: true },
        shortcutDisplay: 'Ctrl+F',
        onClick: () => onMenuItemClick?.('edit', 'find')
      },
      {
        id: 'replace',
        label: 'Replace',
        shortcut: { key: 'h', ctrlKey: true },
        shortcutDisplay: 'Ctrl+H',
        onClick: () => onMenuItemClick?.('edit', 'replace')
      }
    ]
  },
  {
    id: 'view',
    label: 'View',
    items: [
      {
        id: 'toggle-panel-left',
        label: 'Toggle Left Panel',
        shortcut: { key: '1', ctrlKey: true },
        shortcutDisplay: 'Ctrl+1',
        onClick: () => onMenuItemClick?.('view', 'toggle-panel-left')
      },
      {
        id: 'toggle-panel-right',
        label: 'Toggle Right Panel',
        shortcut: { key: '2', ctrlKey: true },
        shortcutDisplay: 'Ctrl+2',
        onClick: () => onMenuItemClick?.('view', 'toggle-panel-right')
      },
      {
        id: 'toggle-panel-bottom',
        label: 'Toggle Bottom Panel',
        shortcut: { key: '3', ctrlKey: true },
        shortcutDisplay: 'Ctrl+3',
        onClick: () => onMenuItemClick?.('view', 'toggle-panel-bottom')
      },
      { id: 'separator-1', label: '', separator: true },
      {
        id: 'zoom-in',
        label: 'Zoom In',
        shortcut: { key: '=', ctrlKey: true },
        shortcutDisplay: 'Ctrl+=',
        onClick: () => onMenuItemClick?.('view', 'zoom-in')
      },
      {
        id: 'zoom-out',
        label: 'Zoom Out',
        shortcut: { key: '-', ctrlKey: true },
        shortcutDisplay: 'Ctrl+-',
        onClick: () => onMenuItemClick?.('view', 'zoom-out')
      },
      {
        id: 'zoom-reset',
        label: 'Reset Zoom',
        shortcut: { key: '0', ctrlKey: true },
        shortcutDisplay: 'Ctrl+0',
        onClick: () => onMenuItemClick?.('view', 'zoom-reset')
      },
      { id: 'separator-2', label: '', separator: true },
      {
        id: 'fullscreen',
        label: 'Toggle Fullscreen',
        shortcut: { key: 'F11' },
        shortcutDisplay: 'F11',
        onClick: () => onMenuItemClick?.('view', 'fullscreen')
      }
    ]
  },
  {
    id: 'layout',
    label: 'Layout',
    items: [
      {
        id: 'preset-standard',
        label: 'Standard Layout',
        onClick: () => onMenuItemClick?.('layout', 'preset-standard')
      },
      {
        id: 'preset-h-layout',
        label: 'H-Layout',
        onClick: () => onMenuItemClick?.('layout', 'preset-h-layout')
      },
      {
        id: 'preset-ide',
        label: 'IDE Layout',
        onClick: () => onMenuItemClick?.('layout', 'preset-ide')
      },
      { id: 'separator-1', label: '', separator: true },
      {
        id: 'custom',
        label: 'Custom Layouts',
        submenu: [
          {
            id: 'save-current',
            label: 'Save Current Layout...',
            onClick: () => onMenuItemClick?.('layout', 'save-current')
          },
          {
            id: 'manage-custom',
            label: 'Manage Custom Layouts...',
            onClick: () => onMenuItemClick?.('layout', 'manage-custom')
          }
        ]
      },
      { id: 'separator-2', label: '', separator: true },
      {
        id: 'reset-layout',
        label: 'Reset Layout',
        onClick: () => onMenuItemClick?.('layout', 'reset-layout')
      },
      {
        id: 'export-layout',
        label: 'Export Layout',
        onClick: () => onMenuItemClick?.('layout', 'export-layout')
      },
      {
        id: 'import-layout',
        label: 'Import Layout',
        onClick: () => onMenuItemClick?.('layout', 'import-layout')
      }
    ]
  }
];

export const ICUIMenuBar: React.FC<ICUIMenuBarProps> = ({
  menus,
  onMenuItemClick,
  className = '',
  style,
  showKeyboardShortcuts = true,
  disabled = false
}) => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const [activeSubmenu, setActiveSubmenu] = useState<string | null>(null);
  const menuBarRef = useRef<HTMLDivElement>(null);
  const menuRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Use provided menus or default ones
  const effectiveMenus = menus || createDefaultMenus(onMenuItemClick);

  // Handle menu toggle
  const handleMenuToggle = useCallback((menuId: string) => {
    if (disabled) return;
    
    setActiveMenu(prev => prev === menuId ? null : menuId);
    setActiveSubmenu(null);
  }, [disabled]);

  // Handle menu item click
  const handleMenuItemClick = useCallback((menuId: string, item: ICUIMenuBarItem, parentItemId?: string) => {
    if (disabled || item.disabled) return;
    
    // If item has submenu, toggle submenu
    if (item.submenu) {
      const submenuId = parentItemId ? `${parentItemId}-${item.id}` : `${menuId}-${item.id}`;
      setActiveSubmenu(prev => prev === submenuId ? null : submenuId);
      return;
    }

    // Close menus and execute action
    setActiveMenu(null);
    setActiveSubmenu(null);

    // Execute item onClick if provided
    if (item.onClick) {
      try {
        item.onClick();
      } catch (error) {
        console.error('Menu item click error:', error);
        notificationService.error(`Menu action failed: ${error.message}`);
      }
    }

    // Notify parent
    onMenuItemClick?.(menuId, item.id);
  }, [disabled, onMenuItemClick]);

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuBarRef.current && !menuBarRef.current.contains(event.target as Node)) {
        setActiveMenu(null);
        setActiveSubmenu(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard shortcuts
  useEffect(() => {
    if (disabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (event.target instanceof HTMLInputElement || 
          event.target instanceof HTMLTextAreaElement ||
          (event.target as HTMLElement)?.contentEditable === 'true') {
        return;
      }

      // Check all menu items for shortcut matches
      for (const menu of effectiveMenus) {
        for (const item of menu.items) {
          if (item.shortcut && matchesShortcut(event, item.shortcut)) {
            event.preventDefault();
            event.stopPropagation();
            handleMenuItemClick(menu.id, item);
            return;
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [effectiveMenus, handleMenuItemClick, disabled]);

  // Check if keyboard event matches shortcut
  const matchesShortcut = (event: KeyboardEvent, shortcut: ICUIMenuBarShortcut): boolean => {
    const key = event.key.toLowerCase();
    const shortcutKey = shortcut.key.toLowerCase();
    
    return (
      key === shortcutKey &&
      !!event.ctrlKey === !!shortcut.ctrlKey &&
      !!event.metaKey === !!shortcut.metaKey &&
      !!event.shiftKey === !!shortcut.shiftKey &&
      !!event.altKey === !!shortcut.altKey
    );
  };

  // Render menu item
  const renderMenuItem = (item: ICUIMenuBarItem, menuId: string, parentItemId?: string) => {
    if (item.separator) {
      return (
        <div
          key={item.id}
          className="h-px my-1 mx-2"
          style={{ backgroundColor: 'var(--icui-border-subtle)' }}
        />
      );
    }

    const hasSubmenu = item.submenu && item.submenu.length > 0;
    const submenuId = parentItemId ? `${parentItemId}-${item.id}` : `${menuId}-${item.id}`;
    const isSubmenuActive = activeSubmenu === submenuId;

    return (
      <div key={item.id} className="relative">
        <button
          className={`w-full text-left px-3 py-2 text-sm transition-colors flex items-center justify-between
            ${item.disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-opacity-10'}`}
          style={{
            color: item.disabled ? 'var(--icui-text-muted)' : 'var(--icui-text-primary)',
            backgroundColor: isSubmenuActive ? 'var(--icui-accent-hover)' : 'transparent'
          }}
          onClick={() => handleMenuItemClick(menuId, item, parentItemId)}
          onMouseEnter={() => hasSubmenu && setActiveSubmenu(submenuId)}
          disabled={item.disabled}
        >
          <span>{item.label}</span>
          <div className="flex items-center gap-2">
            {showKeyboardShortcuts && item.shortcutDisplay && (
              <span
                className="text-xs opacity-70"
                style={{ color: 'var(--icui-text-muted)' }}
              >
                {item.shortcutDisplay}
              </span>
            )}
            {hasSubmenu && (
              <span className="text-xs">▶</span>
            )}
          </div>
        </button>

        {/* Render submenu */}
        {hasSubmenu && isSubmenuActive && (
          <div
            className="absolute left-full top-0 ml-1 min-w-[180px] rounded-md shadow-lg border z-50"
            style={{
              backgroundColor: 'var(--icui-bg-primary)',
              borderColor: 'var(--icui-border)',
            }}
          >
            <div className="py-1">
              {item.submenu!.map(subItem => renderMenuItem(subItem, menuId, submenuId))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      ref={menuBarRef}
      className={`icui-menu-bar flex items-center px-2 py-1 border-b ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderBottomColor: 'var(--icui-border)',
        userSelect: 'none',
        ...style
      }}
    >
      {effectiveMenus.map(menu => (
        <div key={menu.id} className="relative">
          <button
            className={`px-3 py-1 text-sm rounded transition-colors
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-opacity-10'}`}
            style={{
              color: 'var(--icui-text-primary)',
              backgroundColor: activeMenu === menu.id ? 'var(--icui-accent-hover)' : 'transparent'
            }}
            onClick={() => handleMenuToggle(menu.id)}
            disabled={disabled}
          >
            {menu.label}
          </button>

          {/* Dropdown menu */}
          {activeMenu === menu.id && (
            <>
              {/* Backdrop for mobile */}
              <div 
                className="fixed inset-0 z-10 sm:hidden"
                onClick={() => setActiveMenu(null)}
              />
              
              <div
                ref={(el) => el && menuRefs.current.set(menu.id, el)}
                className="absolute top-full left-0 z-20 mt-1 min-w-[200px] rounded-md shadow-lg border"
                style={{
                  backgroundColor: 'var(--icui-bg-primary)',
                  borderColor: 'var(--icui-border)',
                }}
                onMouseLeave={() => setActiveSubmenu(null)}
              >
                <div className="py-1">
                  {menu.items.map(item => renderMenuItem(item, menu.id))}
                </div>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
};

export default ICUIMenuBar;
