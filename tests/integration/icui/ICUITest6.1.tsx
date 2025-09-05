/**
 * ICUI Test 6.1 - MenuBar Test Page
 * 
 * Test page for the ICUI MenuBar component demonstrating all menu functionality,
 * keyboard shortcuts, and integration with the ICUI framework.
 */

import React, { useState, useCallback } from 'react';
import ICUIMenuBar from '../../../src/icui/components/archived/MenuBar_deprecate';
import { notificationService, useNotifications } from '../../../src/icui/services/notificationService';

const ICUITest6_1: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [showShortcuts, setShowShortcuts] = useState(true);
  const [menuDisabled, setMenuDisabled] = useState(false);
  const notifications = useNotifications();

  // Add log entry
  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev.slice(-9), `[${timestamp}] ${message}`]);
  }, []);

  // Handle menu item clicks
  const handleMenuItemClick = useCallback((menuId: string, itemId: string) => {
    const message = `Menu clicked: ${menuId} -> ${itemId}`;
    addLog(message);
    
    // Handle specific menu actions for demonstration
    switch (`${menuId}-${itemId}`) {
      case 'file-new':
        notificationService.success('New file created');
        break;
      case 'file-open':
        notificationService.info('Open file dialog would appear');
        break;
      case 'file-save':
        notificationService.success('File saved');
        break;
      case 'file-settings':
        notificationService.info('Settings dialog would open');
        break;
      case 'edit-undo':
        notificationService.info('Undo operation');
        break;
      case 'edit-redo':
        notificationService.info('Redo operation');
        break;
      case 'edit-copy':
        notificationService.success('Content copied to clipboard');
        break;
      case 'view-toggle-panel-left':
        notificationService.info('Left panel toggled');
        break;
      case 'view-fullscreen':
        notificationService.info('Fullscreen mode toggled');
        break;
      case 'layout-preset-standard':
        notificationService.success('Standard layout applied');
        break;
      case 'layout-preset-h-layout':
        notificationService.success('H-Layout applied');
        break;
      case 'layout-save-current':
        notificationService.info('Save current layout dialog would appear');
        break;
      case 'layout-reset-layout':
        notificationService.warning('Layout reset to default');
        break;
      default:
        notificationService.info(`Action: ${menuId} -> ${itemId}`);
    }
  }, [addLog]);

  // Clear logs
  const handleClearLogs = useCallback(() => {
    setLogs([]);
    addLog('Logs cleared');
  }, [addLog]);

  // Custom menu configuration
  const customMenus = [
    {
      id: 'demo',
      label: 'Demo',
      items: [
        {
          id: 'show-notification',
          label: 'Show Notification',
          onClick: () => {
            notificationService.info('This is a custom menu notification!');
            addLog('Custom notification triggered');
          }
        },
        {
          id: 'show-error',
          label: 'Show Error',
          onClick: () => {
            notificationService.error('This is a demo error');
            addLog('Demo error triggered');
          }
        },
        { id: 'separator-1', label: '', separator: true },
        {
          id: 'submenu-demo',
          label: 'Submenu Demo',
          submenu: [
            {
              id: 'submenu-item-1',
              label: 'Submenu Item 1',
              onClick: () => {
                notificationService.success('Submenu Item 1 clicked');
                addLog('Submenu Item 1 clicked');
              }
            },
            {
              id: 'submenu-item-2',
              label: 'Submenu Item 2',
              onClick: () => {
                notificationService.success('Submenu Item 2 clicked');
                addLog('Submenu Item 2 clicked');
              }
            }
          ]
        }
      ]
    }
  ];

  return (
    <div className="icui-test-6-1 w-full h-screen flex flex-col" style={{ backgroundColor: 'var(--icui-bg-primary)' }}>
      {/* Header */}
      <div className="p-4 border-b" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderBottomColor: 'var(--icui-border)' }}>
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--icui-text-primary)' }}>
          ICUI Test 6.1 - MenuBar Component
        </h1>
        <p className="text-sm" style={{ color: 'var(--icui-text-muted)' }}>
          Testing the ICUI MenuBar component with File, Edit, View, and Layout menus, including keyboard shortcuts and custom menus.
        </p>
      </div>

      {/* Menu Bar */}
      <ICUIMenuBar
        menus={[
          // Include default menus and custom menu
          ...customMenus
        ]}
        onMenuItemClick={handleMenuItemClick}
        showKeyboardShortcuts={showShortcuts}
        disabled={menuDisabled}
      />

      {/* Content Area */}
      <div className="flex-1 flex">
        {/* Main Content */}
        <div className="flex-1 p-4">
          <div className="mb-4">
            <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--icui-text-primary)' }}>
              Menu Bar Test
            </h2>
            <p className="text-sm mb-4" style={{ color: 'var(--icui-text-secondary)' }}>
              Test the menu bar functionality by clicking on menu items or using keyboard shortcuts.
            </p>

            {/* Control Panel */}
            <div className="flex flex-wrap gap-4 mb-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={showShortcuts}
                  onChange={(e) => setShowShortcuts(e.target.checked)}
                  className="rounded"
                />
                <span style={{ color: 'var(--icui-text-primary)' }}>Show Keyboard Shortcuts</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={menuDisabled}
                  onChange={(e) => setMenuDisabled(e.target.checked)}
                  className="rounded"
                />
                <span style={{ color: 'var(--icui-text-primary)' }}>Disable Menu Bar</span>
              </label>
            </div>

            {/* Keyboard Shortcuts Reference */}
            <div className="mb-4 p-4 rounded-lg border" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border)' }}>
              <h3 className="font-medium mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                Keyboard Shortcuts:
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 text-sm">
                <div style={{ color: 'var(--icui-text-secondary)' }}>
                  <strong>File:</strong> Ctrl+N (New), Ctrl+O (Open), Ctrl+S (Save)
                </div>
                <div style={{ color: 'var(--icui-text-secondary)' }}>
                  <strong>Edit:</strong> Ctrl+Z (Undo), Ctrl+Y (Redo), Ctrl+C (Copy)
                </div>
                <div style={{ color: 'var(--icui-text-secondary)' }}>
                  <strong>View:</strong> Ctrl+1/2/3 (Toggle Panels), F11 (Fullscreen)
                </div>
              </div>
            </div>

            {/* Test Actions */}
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                onClick={() => notificationService.success('Test success notification')}
                className="px-3 py-2 text-sm rounded transition-colors"
                style={{ 
                  backgroundColor: 'var(--icui-accent)', 
                  color: 'var(--icui-text-on-accent)',
                  border: 'none'
                }}
              >
                Test Success Notification
              </button>
              <button
                onClick={() => notificationService.error('Test error notification')}
                className="px-3 py-2 text-sm rounded transition-colors"
                style={{ 
                  backgroundColor: 'var(--icui-error)', 
                  color: 'var(--icui-text-on-error)',
                  border: 'none'
                }}
              >
                Test Error Notification
              </button>
              <button
                onClick={() => notificationService.warning('Test warning notification')}
                className="px-3 py-2 text-sm rounded transition-colors"
                style={{ 
                  backgroundColor: 'var(--icui-warning)', 
                  color: 'var(--icui-text-on-warning)',
                  border: 'none'
                }}
              >
                Test Warning Notification
              </button>
            </div>
          </div>

          {/* Activity Logs */}
          <div className="border rounded-lg p-4" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border)' }}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium" style={{ color: 'var(--icui-text-primary)' }}>
                Activity Log
              </h3>
              <button
                onClick={handleClearLogs}
                className="text-xs px-2 py-1 rounded hover:opacity-80 transition-opacity"
                style={{ 
                  backgroundColor: 'var(--icui-accent)', 
                  color: 'var(--icui-text-on-accent)',
                  border: 'none'
                }}
              >
                Clear
              </button>
            </div>
            <div className="h-48 overflow-y-auto border rounded p-2" style={{ backgroundColor: 'var(--icui-bg-primary)', borderColor: 'var(--icui-border-subtle)' }}>
              {logs.length === 0 ? (
                <p className="text-sm" style={{ color: 'var(--icui-text-muted)' }}>
                  No activity yet. Click menu items or use keyboard shortcuts to see logs.
                </p>
              ) : (
                <div className="space-y-1">
                  {logs.map((log, index) => (
                    <div
                      key={index}
                      className="text-xs font-mono"
                      style={{ color: 'var(--icui-text-secondary)' }}
                    >
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Side Panel - Menu Information */}
        <div className="w-80 p-4 border-l" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderLeftColor: 'var(--icui-border)' }}>
          <h3 className="font-medium mb-4" style={{ color: 'var(--icui-text-primary)' }}>
            MenuBar Features
          </h3>
          <div className="space-y-4 text-sm">
            <div>
              <h4 className="font-medium mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                Default Menus:
              </h4>
              <ul className="space-y-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <li>• <strong>File:</strong> New, Open, Save, Settings</li>
                <li>• <strong>Edit:</strong> Undo, Redo, Copy, Paste, Find</li>
                <li>• <strong>View:</strong> Toggle Panels, Zoom, Fullscreen</li>
                <li>• <strong>Layout:</strong> Presets, Custom, Export/Import</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-medium mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                Features Tested:
              </h4>
              <ul className="space-y-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <li>✅ Menu dropdown functionality</li>
                <li>✅ Keyboard shortcuts</li>
                <li>✅ Custom menu integration</li>
                <li>✅ Submenu support</li>
                <li>✅ Menu item disable/enable</li>
                <li>✅ ICUI theming integration</li>
                <li>✅ Notification integration</li>
                <li>✅ Click outside to close</li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium mb-2" style={{ color: 'var(--icui-text-primary)' }}>
                Implementation Status:
              </h4>
              <ul className="space-y-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <li>✅ Phase 6.1: Top Menu Bar - COMPLETE</li>
                <li>⏳ Phase 6.2: File Menu Implementation</li>
                <li>⏳ Phase 6.3: Layout Menu Implementation</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Notification Container */}
      {notifications.notifications.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {notifications.notifications.map((notification) => (
            <div
              key={notification.id}
              className={`px-4 py-3 rounded-lg shadow-lg border transition-all duration-300 max-w-sm ${
                notification.type === 'error' ? 'border-red-500' :
                notification.type === 'warning' ? 'border-yellow-500' :
                notification.type === 'success' ? 'border-green-500' :
                'border-blue-500'
              }`}
              style={{
                backgroundColor: 
                  notification.type === 'error' ? 'var(--icui-error)' :
                  notification.type === 'warning' ? 'var(--icui-warning)' :
                  notification.type === 'success' ? 'var(--icui-success)' :
                  'var(--icui-info)',
                color: 'white'
              }}
            >
              <div className="text-sm font-medium">{notification.message}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ICUITest6_1;
