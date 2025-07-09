/**
 * ICUI Panel Selector Component
 * Provides a dropdown interface for selecting and adding new panels
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';

export interface ICUIPanelType {
  id: string;
  name: string;
  icon: string;
  description?: string;
}

export interface ICUIPanelSelectorProps {
  panelTypes: ICUIPanelType[];
  onPanelSelect: (panelType: ICUIPanelType) => void;
  className?: string;
  buttonClassName?: string;
  dropdownClassName?: string;
  disabled?: boolean;
  placeholder?: string;
}

export const ICUIPanelSelector: React.FC<ICUIPanelSelectorProps> = ({
  panelTypes,
  onPanelSelect,
  className = '',
  buttonClassName = '',
  dropdownClassName = '',
  disabled = false,
  placeholder = 'Add Panel',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, right: 0 });
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Calculate dropdown position when opening
  useEffect(() => {
    if (isOpen && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + 4,
        right: window.innerWidth - rect.right
      });
    }
  }, [isOpen]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleToggle = useCallback(() => {
    if (!disabled) {
      setIsOpen(!isOpen);
    }
  }, [disabled, isOpen]);

  const handlePanelSelect = useCallback((panelType: ICUIPanelType) => {
    onPanelSelect(panelType);
    setIsOpen(false);
  }, [onPanelSelect]);

  return (
    <div className={`icui-panel-selector relative ${className}`} ref={dropdownRef}>
      {/* Toggle Button */}
      <button
        ref={buttonRef}
        type="button"
        className={`
          icui-panel-selector-button
          px-2 py-1 text-sm 
          disabled:opacity-50 disabled:cursor-not-allowed
          border rounded-none transition-colors
          flex items-center justify-center
          ${buttonClassName}
        `}
        style={{
          backgroundColor: 'var(--icui-bg-secondary)',
          borderColor: 'var(--icui-border-subtle)',
          color: 'var(--icui-text-primary)'
        }}
        onClick={handleToggle}
        disabled={disabled}
        title={disabled ? 'Cannot add panels' : 'Add new panel'}
      >
        <span className="text-xs">▼</span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className={`
          icui-panel-selector-dropdown
          absolute top-full right-0 mt-1 
          border rounded shadow-lg
          min-w-[200px] max-w-[300px] z-[9999]
          ${dropdownClassName}
        `}
        style={{ 
          position: 'fixed',
          top: dropdownPosition.top,
          right: dropdownPosition.right,
          zIndex: 9999,
          backgroundColor: 'var(--icui-bg-primary)',
          borderColor: 'var(--icui-border-subtle)',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}
        >
          {panelTypes.length === 0 ? (
            <div className="px-3 py-2 text-sm text-center" style={{ color: 'var(--icui-text-muted)' }}>
              No panels available
            </div>
          ) : (
            panelTypes.map((panelType) => (
              <button
                key={panelType.id}
                type="button"
                className="
                  w-full px-3 py-2 text-left text-sm
                  hover:bg-opacity-80 transition-colors
                  flex items-center gap-2
                  first:rounded-t last:rounded-b
                "
                style={{
                  backgroundColor: 'transparent',
                  color: 'var(--icui-text-primary)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
                onClick={() => handlePanelSelect(panelType)}
              >
                <span className="text-base">{panelType.icon}</span>
                <div className="flex-1">
                  <div className="font-medium">{panelType.name}</div>
                  {panelType.description && (
                    <div className="text-xs" style={{ color: 'var(--icui-text-muted)' }}>{panelType.description}</div>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default ICUIPanelSelector; 