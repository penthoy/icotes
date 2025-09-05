/**
 * ICUI Context Menu Component
 * 
 * Reusable context menu UI that renders from schema with visibility/enabled predicates.
 * Supports nested submenus, separators, icons, shortcuts, confirm dialogs for dangerous actions.
 * Positioning (mouse-based, anchor-based), portal rendering, auto-flip.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { MenuItem, MenuSchema, MenuContext } from '../../lib/menuSchemas';
import { useTheme } from '../../lib/theming';
import { getMenuItemAriaProps, useKeyboardNavigation } from '../../lib/accessibility';

export interface ContextMenuProps {
  schema: MenuSchema;
  context: MenuContext;
  visible: boolean;
  position: { x: number; y: number };
  onClose: () => void;
  onItemClick: (item: MenuItem) => void;
  anchorElement?: HTMLElement;
}

export interface ContextMenuState {
  focusedIndex: number;
  openSubMenu: string | null;
  subMenuPosition: { x: number; y: number } | null;
}

/**
 * Individual menu item component
 */
const ContextMenuItem: React.FC<{
  item: MenuItem;
  context: MenuContext;
  focused: boolean;
  onSelect: (item: MenuItem) => void;
  onMouseEnter: () => void;
  onOpenSubMenu: (item: MenuItem, position: { x: number; y: number }) => void;
  onCloseSubMenu: () => void;
}> = ({ 
  item, 
  context, 
  focused, 
  onSelect, 
  onMouseEnter, 
  onOpenSubMenu, 
  onCloseSubMenu 
}) => {
  const { theme } = useTheme();
  const itemRef = useRef<HTMLDivElement>(null);

  const isVisible = item.isVisible ? item.isVisible(context) : true;
  const isEnabled = item.isEnabled ? item.isEnabled(context) : true;

  useEffect(() => {
    if (focused && itemRef.current) {
      itemRef.current.focus();
    }
  }, [focused]);

  if (!isVisible) {
    return null;
  }

  if (item.separator) {
    return (
      <div 
        className="icui-context-menu-separator"
        style={{
          height: '1px',
          backgroundColor: theme.colors.border.primary,
          margin: `${theme.spacing.xs} 0`,
        }}
      />
    );
  }

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!isEnabled) return;
    
    if (item.children && item.children.length > 0) {
      const rect = itemRef.current?.getBoundingClientRect();
      if (rect) {
        onOpenSubMenu(item, { x: rect.right, y: rect.top });
      }
    } else {
      onSelect(item);
    }
  }, [item, isEnabled, onSelect, onOpenSubMenu]);

  const handleMouseEnter = useCallback(() => {
    onMouseEnter();
    if (item.children && item.children.length > 0) {
      const rect = itemRef.current?.getBoundingClientRect();
      if (rect) {
        onOpenSubMenu(item, { x: rect.right, y: rect.top });
      }
    } else {
      onCloseSubMenu();
    }
  }, [onMouseEnter, item, onOpenSubMenu, onCloseSubMenu]);

  const ariaProps = getMenuItemAriaProps({
    selected: focused,
    disabled: !isEnabled,
    level: 1,
    setSize: 1,
    posInSet: 1,
  });

  return (
    <div
      ref={itemRef}
      className={`icui-context-menu-item ${focused ? 'focused' : ''} ${!isEnabled ? 'disabled' : ''} ${item.danger ? 'danger' : ''}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
        cursor: isEnabled ? 'pointer' : 'not-allowed',
        backgroundColor: focused && isEnabled ? theme.colors.interactive.primaryHover : 'transparent',
        color: isEnabled ? 
          (item.danger ? theme.colors.status.error : theme.colors.text.primary) :
          theme.colors.text.disabled,
        fontSize: theme.typography.fontSize.base,
        lineHeight: theme.typography.lineHeight.normal,
        userSelect: 'none',
        borderRadius: theme.borderRadius.sm,
        margin: `1px ${theme.spacing.xs}`,
      }}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      tabIndex={focused ? 0 : -1}
      {...ariaProps}
    >
      {item.icon && (
        <span 
          className="icui-context-menu-icon"
          style={{ 
            marginRight: theme.spacing.sm,
            fontSize: '14px',
            width: '16px',
            textAlign: 'center',
          }}
        >
          {item.icon}
        </span>
      )}
      
      <span 
        className="icui-context-menu-label"
        style={{ flex: 1 }}
      >
        {item.label}
      </span>
      
      {item.shortcut && (
        <span 
          className="icui-context-menu-shortcut"
          style={{
            marginLeft: theme.spacing.md,
            fontSize: '12px',
            color: theme.colors.text.secondary,
          }}
        >
          {item.shortcut}
        </span>
      )}
      
      {item.children && item.children.length > 0 && (
        <span 
          className="icui-context-menu-arrow"
          style={{
            marginLeft: theme.spacing.sm,
            color: theme.colors.text.secondary,
          }}
        >
          ▶
        </span>
      )}
    </div>
  );
};

/**
 * Main context menu component
 */
export const ContextMenu: React.FC<ContextMenuProps> = ({
  schema,
  context,
  visible,
  position,
  onClose,
  onItemClick,
  anchorElement,
}) => {
  const { theme } = useTheme();
  const menuRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<ContextMenuState>({
    focusedIndex: -1,
    openSubMenu: null,
    subMenuPosition: null,
  });

  // Filter visible items
  const visibleItems = schema.items.filter(item => 
    item.isVisible ? item.isVisible(context) : true
  );

  // Keyboard navigation
  const { focusedIndex, handleKeyDown } = useKeyboardNavigation({
    items: visibleItems.map((item, index) => ({ 
      id: item.id, 
      disabled: item.isEnabled ? !item.isEnabled(context) : false 
    })),
    onSelect: (id) => {
      const item = visibleItems.find(item => item.id === id);
      if (item) {
        handleItemClick(item);
      }
    },
    onActivate: (id) => {
      const item = visibleItems.find(item => item.id === id);
      if (item) {
        handleItemClick(item);
      }
    },
  });

  // Position calculation with auto-flip
  const calculatePosition = useCallback(() => {
    if (!menuRef.current) return position;

    const menuRect = menuRef.current.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    let { x, y } = position;

    // Auto-flip horizontally
    if (x + menuRect.width > viewportWidth) {
      x = Math.max(0, x - menuRect.width);
    }

    // Auto-flip vertically  
    if (y + menuRect.height > viewportHeight) {
      y = Math.max(0, y - menuRect.height);
    }

    return { x, y };
  }, [position]);

  // Handle item selection
  const handleItemClick = useCallback((item: MenuItem) => {
    if (item.danger) {
      // Show confirmation dialog for dangerous actions
      const confirmed = window.confirm(`Are you sure you want to ${item.label.toLowerCase()}?`);
      if (!confirmed) return;
    }
    
    onItemClick(item);
    onClose();
  }, [onItemClick, onClose]);

  // Handle submenu operations
  const handleOpenSubMenu = useCallback((item: MenuItem, subMenuPosition: { x: number; y: number }) => {
    setState(prev => ({
      ...prev,
      openSubMenu: item.id,
      subMenuPosition,
    }));
  }, []);

  const handleCloseSubMenu = useCallback(() => {
    setState(prev => ({
      ...prev,
      openSubMenu: null,
      subMenuPosition: null,
    }));
  }, []);

  // Close on outside clicks
  useEffect(() => {
    if (!visible) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [visible, onClose]);

  // Focus management
  useEffect(() => {
    if (visible && menuRef.current) {
      menuRef.current.focus();
    }
  }, [visible]);

  if (!visible) return null;

  const finalPosition = calculatePosition();

  const menuElement = (
    <div
      ref={menuRef}
      className="icui-context-menu"
      style={{
        position: 'fixed',
        top: finalPosition.y,
        left: finalPosition.x,
        backgroundColor: theme.colors.bg.primary,
        border: `1px solid ${theme.colors.border.primary}`,
        borderRadius: theme.borderRadius.md,
        boxShadow: theme.shadows.lg,
        padding: `${theme.spacing.xs} 0`,
        minWidth: '200px',
        maxWidth: '300px',
        zIndex: 10000,
        outline: 'none',
      }}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
      role="menu"
      aria-labelledby="context-menu"
    >
      {visibleItems.map((item, index) => (
        <ContextMenuItem
          key={item.id}
          item={item}
          context={context}
          focused={index === focusedIndex}
          onSelect={handleItemClick}
          onMouseEnter={() => setState(prev => ({ ...prev, focusedIndex: index }))}
          onOpenSubMenu={handleOpenSubMenu}
          onCloseSubMenu={handleCloseSubMenu}
        />
      ))}
    </div>
  );

  // Render submenu if open
  const subMenuElement = state.openSubMenu && state.subMenuPosition && (() => {
    const parentItem = visibleItems.find(item => item.id === state.openSubMenu);
    if (!parentItem || !parentItem.children) return null;

    const subSchema: MenuSchema = {
      id: `${schema.id}-${state.openSubMenu}`,
      items: parentItem.children,
    };

    return (
      <ContextMenu
        schema={subSchema}
        context={context}
        visible={true}
        position={state.subMenuPosition}
        onClose={handleCloseSubMenu}
        onItemClick={onItemClick}
      />
    );
  })();

  return createPortal(
    <>
      {menuElement}
      {subMenuElement}
    </>,
    document.body
  );
};

/**
 * Hook for using context menus
 */
export function useContextMenu() {
  const [contextMenu, setContextMenu] = useState<{
    schema: MenuSchema;
    context: MenuContext;
    position: { x: number; y: number };
  } | null>(null);

  const showContextMenu = useCallback((
    event: React.MouseEvent,
    schema: MenuSchema,
    context: MenuContext
  ) => {
    event.preventDefault();
    event.stopPropagation();
    
    setContextMenu({
      schema,
      context,
      position: { x: event.clientX, y: event.clientY },
    });
  }, []);

  const hideContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  return {
    contextMenu,
    showContextMenu,
    hideContextMenu,
  };
}

export default ContextMenu;
