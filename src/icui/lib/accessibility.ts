/**
 * ICUI Accessibility Foundation
 * 
 * Accessibility utilities and hooks for ICUI components.
 * Includes ARIA support, keyboard navigation, screen reader support.
 */

import { useEffect, useRef, useState } from 'react';
import type React from 'react';

/**
 * ARIA roles for ICUI components
 */
export const AriaRoles = {
  TOOLBAR: 'toolbar',
  MENUBAR: 'menubar',
  MENU: 'menu',
  MENUITEM: 'menuitem',
  BUTTON: 'button',
  TAB: 'tab',
  TABLIST: 'tablist',
  TABPANEL: 'tabpanel',
  TREE: 'tree',
  TREEITEM: 'treeitem',
  LISTBOX: 'listbox',
  OPTION: 'option',
  DIALOG: 'dialog',
  REGION: 'region',
} as const;

/**
 * ARIA states and properties
 */
export interface AriaProps {
  'aria-label'?: string;
  'aria-labelledby'?: string;
  'aria-describedby'?: string;
  'aria-expanded'?: boolean;
  'aria-selected'?: boolean;
  'aria-checked'?: boolean;
  'aria-disabled'?: boolean;
  'aria-hidden'?: boolean;
  'aria-current'?: 'page' | 'step' | 'location' | 'date' | 'time' | 'true' | 'false';
  'aria-live'?: 'off' | 'polite' | 'assertive';
  'aria-atomic'?: boolean;
  'aria-busy'?: boolean;
  'aria-controls'?: string;
  'aria-owns'?: string;
  'aria-haspopup'?: boolean | 'false' | 'true' | 'menu' | 'listbox' | 'tree' | 'grid' | 'dialog';
  'aria-orientation'?: 'horizontal' | 'vertical';
  'aria-multiselectable'?: boolean;
  'aria-level'?: number;
  'aria-setsize'?: number;
  'aria-posinset'?: number;
  role?: string;
  tabIndex?: number;
}

/**
 * Generate ARIA props for menu items
 */
export function getMenuItemAriaProps(options: {
  selected?: boolean;
  expanded?: boolean;
  disabled?: boolean;
  hasSubmenu?: boolean;
  level?: number;
  setSize?: number;
  posInSet?: number;
}): AriaProps {
  const {
    selected = false,
    expanded,
    disabled = false,
    hasSubmenu = false,
    level,
    setSize,
    posInSet,
  } = options;

  return {
    role: AriaRoles.MENUITEM,
    'aria-selected': selected,
    'aria-expanded': hasSubmenu ? expanded : undefined,
    'aria-disabled': disabled,
    'aria-haspopup': hasSubmenu ? 'menu' : undefined,
    'aria-level': level,
    'aria-setsize': setSize,
    'aria-posinset': posInSet,
    tabIndex: disabled ? -1 : 0,
  };
}

/**
 * Generate ARIA props for tree items
 */
export function getTreeItemAriaProps(options: {
  selected?: boolean;
  expanded?: boolean;
  level: number;
  setSize: number;
  posInSet: number;
  hasChildren?: boolean;
}): AriaProps {
  const {
    selected = false,
    expanded,
    level,
    setSize,
    posInSet,
    hasChildren = false,
  } = options;

  return {
    role: AriaRoles.TREEITEM,
    'aria-selected': selected,
    'aria-expanded': hasChildren ? expanded : undefined,
    'aria-level': level,
    'aria-setsize': setSize,
    'aria-posinset': posInSet,
    tabIndex: selected ? 0 : -1,
  };
}

/**
 * Generate ARIA props for list options
 */
export function getListOptionAriaProps(options: {
  selected?: boolean;
  disabled?: boolean;
  setSize: number;
  posInSet: number;
}): AriaProps {
  const {
    selected = false,
    disabled = false,
    setSize,
    posInSet,
  } = options;

  return {
    role: AriaRoles.OPTION,
    'aria-selected': selected,
    'aria-disabled': disabled,
    'aria-setsize': setSize,
    'aria-posinset': posInSet,
    tabIndex: disabled ? -1 : 0,
  };
}

/**
 * Hook for managing focus within a component
 */
export function useFocusManager(options: {
  autoFocus?: boolean;
  restoreFocus?: boolean;
} = {}) {
  const { autoFocus = false, restoreFocus = true } = options;
  const containerRef = useRef<HTMLElement>(null);
  const previousActiveElement = useRef<Element | null>(null);

  useEffect(() => {
    if (autoFocus && containerRef.current) {
      previousActiveElement.current = document.activeElement;
      
      // Focus first focusable element
      const firstFocusable = containerRef.current.querySelector(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      ) as HTMLElement;
      
      if (firstFocusable) {
        firstFocusable.focus();
      } else {
        containerRef.current.focus();
      }
    }

    return () => {
      if (restoreFocus && previousActiveElement.current) {
        (previousActiveElement.current as HTMLElement).focus();
      }
    };
  }, [autoFocus, restoreFocus]);

  return containerRef;
}

/**
 * Hook for keyboard navigation in lists/trees
 */
export function useKeyboardNavigation(options: {
  items: Array<{ id: string; disabled?: boolean }>;
  onSelect?: (id: string) => void;
  onActivate?: (id: string) => void;
  orientation?: 'vertical' | 'horizontal';
  loop?: boolean;
}) {
  const {
    items,
    onSelect,
    onActivate,
    orientation = 'vertical',
    loop = true,
  } = options;

  const [focusedIndex, setFocusedIndex] = useState(0);

  const handleKeyDown = (event: React.KeyboardEvent) => {
    const isVertical = orientation === 'vertical';
    const upKey = isVertical ? 'ArrowUp' : 'ArrowLeft';
    const downKey = isVertical ? 'ArrowDown' : 'ArrowRight';

    switch (event.key) {
    case upKey:
        event.preventDefault();
        setFocusedIndex(prev => {
          let newIndex = prev - 1;
          
          // Skip disabled items
          while (newIndex >= 0 && items[newIndex]?.disabled) {
            newIndex--;
          }
          
          if (newIndex < 0) {
            if (loop) {
              // Loop to end
              newIndex = items.length - 1;
              while (newIndex >= 0 && items[newIndex]?.disabled) {
                newIndex--;
              }
            } else {
              newIndex = prev;
            }
          }
          
      return newIndex >= 0 ? newIndex : prev;
        });
        break;

    case downKey:
        event.preventDefault();
        setFocusedIndex(prev => {
          let newIndex = prev + 1;
          
          // Skip disabled items
          while (newIndex < items.length && items[newIndex]?.disabled) {
            newIndex++;
          }
          
          if (newIndex >= items.length) {
            if (loop) {
              // Loop to beginning
              newIndex = 0;
              while (newIndex < items.length && items[newIndex]?.disabled) {
                newIndex++;
              }
            } else {
              newIndex = prev;
            }
          }
          
      return newIndex < items.length ? newIndex : prev;
        });
        break;

      case 'Home':
        event.preventDefault();
        let firstEnabled = 0;
        while (firstEnabled < items.length && items[firstEnabled]?.disabled) {
          firstEnabled++;
        }
        setFocusedIndex(firstEnabled);
        break;

      case 'End':
        event.preventDefault();
        let lastEnabled = items.length - 1;
        while (lastEnabled >= 0 && items[lastEnabled]?.disabled) {
          lastEnabled--;
        }
        setFocusedIndex(Math.max(0, lastEnabled));
        break;

      case 'Enter':
      case ' ':
        event.preventDefault();
        if (items[focusedIndex] && !items[focusedIndex].disabled) {
          if (event.key === 'Enter') {
            onActivate?.(items[focusedIndex].id);
          } else {
            onSelect?.(items[focusedIndex].id);
          }
        }
        break;
    }
  };

  return {
    focusedIndex,
    setFocusedIndex,
    handleKeyDown,
  };
}

/**
 * Hook for managing ARIA live regions
 */
export function useLiveRegion() {
  const [message, setMessage] = useState('');
  const [politeness, setPoliteness] = useState<'polite' | 'assertive'>('polite');

  const announce = (text: string, level: 'polite' | 'assertive' = 'polite') => {
    setPoliteness(level);
    setMessage(''); // Clear first to ensure re-announcement
    
    // Use setTimeout to ensure the message is cleared before setting new one
    setTimeout(() => {
      setMessage(text);
    }, 10);
  };

  const liveRegionProps = {
    'aria-live': politeness,
    'aria-atomic': true,
    style: {
      position: 'absolute' as const,
      left: '-10000px',
      top: 'auto',
      width: '1px',
      height: '1px',
      overflow: 'hidden',
    },
  };

  return {
    announce,
    liveRegionProps,
    message,
  };
}

/**
 * Hook for detecting reduced motion preference
 */
export function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
}

/**
 * Accessibility utilities
 */
export class AccessibilityUtils {
  /**
   * Generate a unique ID for ARIA relationships
   */
  static generateId(prefix = 'icui'): string {
    return `${prefix}-${Math.random().toString(36).slice(2, 11)}`;
  }

  /**
   * Create ARIA label from text content
   */
  static createAriaLabel(text: string, fallback?: string): string {
    // Remove HTML tags and clean up whitespace
    const cleaned = text.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
    return cleaned || fallback || 'Untitled';
  }

  /**
   * Check if element is focusable
   */
  static isFocusable(element: Element): boolean {
    if (element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true') {
      return false;
    }

    const tabIndex = element.getAttribute('tabindex');
    if (tabIndex === '-1') return false;

    // Interactive elements
    const tagName = element.tagName.toLowerCase();
    if (['button', 'input', 'select', 'textarea', 'a'].includes(tagName)) {
      return true;
    }

    // Elements with positive tabindex
    if (tabIndex && parseInt(tabIndex) >= 0) {
      return true;
    }

    return false;
  }

  /**
   * Find all focusable elements within container
   */
  static getFocusableElements(container: Element): HTMLElement[] {
    const selector = [
      'button:not([disabled])',
      '[href]',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');

    return Array.from(container.querySelectorAll(selector))
      .filter(el => AccessibilityUtils.isFocusable(el)) as HTMLElement[];
  }

  /**
   * Trap focus within container
   */
  static trapFocus(container: Element, event: KeyboardEvent): void {
    if (event.key !== 'Tab') return;

    const focusableElements = AccessibilityUtils.getFocusableElements(container);
    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    if (event.shiftKey) {
      // Shift + Tab
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    } else {
      // Tab
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }
}
