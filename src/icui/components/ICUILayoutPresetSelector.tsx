/**
 * ICUI Framework - Layout Preset Selector Component
 * Allows users to select and apply layout presets
 */

import React, { useState } from 'react';
import { useICUILayoutState } from '../hooks/icui-use-layout-state';
import { ICUILayoutPresetType } from '../types/icui-layout-state';

interface ICUILayoutPresetSelectorProps {
  className?: string;
  showExportImport?: boolean;
}

/**
 * Layout Preset Selector Component
 */
export const ICUILayoutPresetSelector: React.FC<ICUILayoutPresetSelectorProps> = ({
  className = '',
  showExportImport = true,
}) => {
  const { layoutState, actions, isLoading, error } = useICUILayoutState();
  const [importText, setImportText] = useState('');
  const [showImportDialog, setShowImportDialog] = useState(false);

  if (isLoading) {
    return (
      <div className={`icui-layout-selector loading ${className}`}>
        <div className="p-4 text-center">
          <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
          <p className="text-sm text-gray-600">Loading layout state...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`icui-layout-selector error ${className}`}>
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-800 text-sm">Error: {error}</p>
        </div>
      </div>
    );
  }

  const handlePresetChange = (presetType: ICUILayoutPresetType) => {
    try {
      actions.applyPreset(presetType);
    } catch (err) {
      console.error('Failed to apply preset:', err);
    }
  };

  const handleExport = () => {
    try {
      if (!layoutState?.currentLayout) {
        alert('No layout to export');
        return;
      }
      
      const exported = actions.exportLayout(layoutState.currentLayout);
      
      // Use modern clipboard API with fallback
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(exported).then(() => {
          alert('Layout exported to clipboard!');
        }).catch(() => {
          // Fallback to textarea method
          fallbackCopyToClipboard(exported);
        });
      } else {
        fallbackCopyToClipboard(exported);
      }
    } catch (err) {
      console.error('Failed to export layout:', err);
      alert(`Failed to export layout: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const fallbackCopyToClipboard = (text: string) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      alert('Layout exported to clipboard!');
    } catch (err) {
      console.error('Fallback copy failed:', err);
      alert('Failed to copy to clipboard. Layout could not be exported.');
    }
    
    document.body.removeChild(textArea);
  };

  const handleImport = () => {
    if (!importText.trim()) return;
    
    try {
      const imported = actions.importLayout(importText);
      actions.saveLayout(imported);
      setImportText('');
      setShowImportDialog(false);
      alert('Layout imported successfully!');
    } catch (err) {
      console.error('Failed to import layout:', err);
      alert('Failed to import layout: Invalid format');
    }
  };

  const currentPreset = layoutState?.currentLayout?.type || 'custom';
  const presets = layoutState?.presets || [];

  return (
    <div className={`icui-layout-selector ${className}`}>
      <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
        <h3 className="text-lg font-semibold mb-4">Layout Presets</h3>
        
        {/* Current Layout Info */}
        <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 rounded">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            <strong>Current:</strong> {layoutState?.currentLayout?.name || 'None'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Type: {currentPreset} | Modified: {
              layoutState?.currentLayout?.modifiedAt 
                ? new Date(layoutState.currentLayout.modifiedAt).toLocaleString()
                : 'Unknown'
            }
          </p>
        </div>

        {/* Preset Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-4">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetChange(preset.type)}
              className={`p-3 text-sm rounded border transition-colors ${
                currentPreset === preset.type
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-200 border-gray-300 dark:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-500'
              }`}
              title={preset.description}
            >
              <div className="font-medium">{preset.name}</div>
              <div className="text-xs opacity-75 mt-1">{preset.description}</div>
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => actions.resetToDefault()}
            className="px-3 py-2 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
          >
            Reset to Default
          </button>
          <button
            onClick={() => actions.undo()}
            className="px-3 py-2 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
          >
            Undo
          </button>
        </div>

        {/* Export/Import */}
        {showExportImport && (
          <div className="border-t border-gray-200 dark:border-gray-600 pt-4">
            <h4 className="font-medium mb-2">Export/Import</h4>
            <div className="flex gap-2 mb-2">
              <button
                onClick={handleExport}
                className="px-3 py-2 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
              >
                Export Current
              </button>
              <button
                onClick={() => setShowImportDialog(!showImportDialog)}
                className="px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                Import Layout
              </button>
            </div>

            {showImportDialog && (
              <div className="mt-3 p-3 border border-gray-300 dark:border-gray-600 rounded">
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder="Paste exported layout JSON here..."
                  className="w-full h-24 p-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={handleImport}
                    disabled={!importText.trim()}
                    className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                  >
                    Import
                  </button>
                  <button
                    onClick={() => {
                      setShowImportDialog(false);
                      setImportText('');
                    }}
                    className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Debug info removed for cleaner development experience */}
      </div>
    </div>
  );
};

export default ICUILayoutPresetSelector;
