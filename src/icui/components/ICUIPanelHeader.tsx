/**
 * ICUI Framework - Panel Header Component
 * Header system with title display, type selector, and control buttons
 */

import React, { useState, useCallback } from 'react';
import { ICUIPanelHeaderProps, ICUIPanelType, ICUIPanelState } from '../types/icui-panel';

// Panel type icons mapping
const PANEL_TYPE_ICONS: Record<ICUIPanelType, string> = {
  terminal: '⌨️',
  editor: '📝',
  explorer: '📁',
  output: '📤',
  properties: '⚙️',
  timeline: '⏱️',
  inspector: '🔍',
  custom: '📋',
};

// Panel type labels
const PANEL_TYPE_LABELS: Record<ICUIPanelType, string> = {
  terminal: 'Terminal',
  editor: 'Editor',
  explorer: 'Explorer',
  output: 'Output',
  properties: 'Properties',
  timeline: 'Timeline',
  inspector: 'Inspector',
  custom: 'Custom',
};

/**
 * Panel Header Component
 * Displays title, type selector, and control buttons
 */
export const ICUIPanelHeader: React.FC<ICUIPanelHeaderProps> = ({
  panel,
  onStateChange,
  onTitleChange,
  onTypeChange,
  onClose,
  onDragStart,
  editable = false,
  showControls = true,
}) => {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [tempTitle, setTempTitle] = useState(panel.config.title);
  const [showTypeSelector, setShowTypeSelector] = useState(false);

  // Handle title edit
  const handleTitleEdit = useCallback(() => {
    if (editable && onTitleChange) {
      setIsEditingTitle(true);
      setTempTitle(panel.config.title);
    }
  }, [editable, onTitleChange, panel.config.title]);

  // Handle title save
  const handleTitleSave = useCallback(() => {
    if (onTitleChange && tempTitle !== panel.config.title) {
      onTitleChange(tempTitle);
    }
    setIsEditingTitle(false);
  }, [onTitleChange, tempTitle, panel.config.title]);

  // Handle title cancel
  const handleTitleCancel = useCallback(() => {
    setTempTitle(panel.config.title);
    setIsEditingTitle(false);
  }, [panel.config.title]);

  // Handle key press in title input
  const handleTitleKeyPress = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleTitleSave();
    } else if (event.key === 'Escape') {
      handleTitleCancel();
    }
  }, [handleTitleSave, handleTitleCancel]);

  // Handle type change
  const handleTypeChange = useCallback((newType: ICUIPanelType) => {
    if (onTypeChange) {
      onTypeChange(newType);
    }
    setShowTypeSelector(false);
  }, [onTypeChange]);

  // Handle minimize
  const handleMinimize = useCallback(() => {
    if (panel.config.minimizable) {
      const newState: ICUIPanelState = panel.state === 'minimized' ? 'normal' : 'minimized';
      onStateChange(newState);
    }
  }, [panel.config.minimizable, panel.state, onStateChange]);

  // Handle maximize
  const handleMaximize = useCallback(() => {
    if (panel.config.maximizable) {
      const newState: ICUIPanelState = panel.state === 'maximized' ? 'normal' : 'maximized';
      onStateChange(newState);
    }
  }, [panel.config.maximizable, panel.state, onStateChange]);

  // Handle close
  const handleClose = useCallback(() => {
    if (panel.config.closable && onClose) {
      onClose();
    }
  }, [panel.config.closable, onClose]);

  const currentIcon = panel.config.icon || PANEL_TYPE_ICONS[panel.config.type];
  const currentLabel = PANEL_TYPE_LABELS[panel.config.type];

  return (
    <div 
      className="icui-panel-header"
      onMouseDown={onDragStart}
    >
      {/* Panel Icon and Type */}
      <div className="icui-panel-type-section">
        <div 
          className="icui-panel-icon"
          onClick={() => setShowTypeSelector(!showTypeSelector)}
          title={`Panel Type: ${currentLabel}`}
        >
          <span className="icui-panel-icon-emoji">{currentIcon}</span>
        </div>
        
        {/* Type Selector Dropdown */}
        {showTypeSelector && onTypeChange && (
          <div className="icui-panel-type-selector">
            {Object.entries(PANEL_TYPE_LABELS).map(([type, label]) => (
              <button
                key={type}
                className={`icui-type-option ${type === panel.config.type ? 'active' : ''}`}
                onClick={() => handleTypeChange(type as ICUIPanelType)}
              >
                <span className="icui-type-icon">{PANEL_TYPE_ICONS[type as ICUIPanelType]}</span>
                <span className="icui-type-label">{label}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Panel Title */}
      <div className="icui-panel-title-section">
        {isEditingTitle ? (
          <input
            type="text"
            value={tempTitle}
            onChange={(e) => setTempTitle(e.target.value)}
            onBlur={handleTitleSave}
            onKeyDown={handleTitleKeyPress}
            className="icui-panel-title-input"
            autoFocus
          />
        ) : (
          <span 
            className="icui-panel-title"
            onDoubleClick={handleTitleEdit}
            title={editable ? 'Double-click to edit' : panel.config.title}
          >
            {panel.config.title}
          </span>
        )}
      </div>

      {/* Panel Controls */}
      {showControls && (
        <div className="icui-panel-controls">
          {/* Minimize Button */}
          {panel.config.minimizable && (
            <button
              className="icui-panel-control icui-minimize-btn"
              onClick={handleMinimize}
              title={panel.state === 'minimized' ? 'Restore' : 'Minimize'}
            >
              {panel.state === 'minimized' ? '⬆️' : '➖'}
            </button>
          )}
          
          {/* Maximize Button */}
          {panel.config.maximizable && (
            <button
              className="icui-panel-control icui-maximize-btn"
              onClick={handleMaximize}
              title={panel.state === 'maximized' ? 'Restore' : 'Maximize'}
            >
              {panel.state === 'maximized' ? '🔽' : '⬆️'}
            </button>
          )}
          
          {/* Close Button */}
          {panel.config.closable && (
            <button
              className="icui-panel-control icui-close-btn"
              onClick={handleClose}
              title="Close"
            >
              ❌
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default ICUIPanelHeader;
