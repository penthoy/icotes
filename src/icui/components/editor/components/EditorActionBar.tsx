/**
 * Editor Action Bar Component
 * 
 * Displays file path, save button, and auto-save toggle
 */

import React from 'react';
import { EditorFile } from '../types';
import { ConnectionStatus } from '../../../services';

interface EditorActionBarProps {
  activeFile: EditorFile;
  effectiveWorkspaceRoot: string;
  isLoading: boolean;
  autoSaveEnabled: boolean;
  connectionStatus: ConnectionStatus;
  onSave: () => void;
  onToggleAutoSave: (enabled: boolean) => void;
}

export const EditorActionBar: React.FC<EditorActionBarProps> = ({
  activeFile,
  effectiveWorkspaceRoot,
  isLoading,
  autoSaveEnabled,
  connectionStatus,
  onSave,
  onToggleAutoSave
}) => {
  return (
    <div className="flex items-center justify-between p-2 border-b icui-editor-actions">
      <div className="flex items-center space-x-4">
        <span className="text-xs font-mono icui-text-secondary">
          {activeFile.path || `${effectiveWorkspaceRoot}/${activeFile.name}`}
        </span>
        {isLoading && (
          <div className="icui-spinner" />
        )}
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={onSave}
          disabled={!activeFile.modified || !connectionStatus.connected || isLoading}
          className="px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed icui-btn-save"
        >
          Save
        </button>
        <div className="flex items-center space-x-1">
          <input
            type="checkbox"
            id="auto-save-checkbox"
            checked={autoSaveEnabled}
            onChange={(e) => onToggleAutoSave(e.target.checked)}
            className="w-3 h-3"
          />
          <label htmlFor="auto-save-checkbox" className="text-xs cursor-pointer icui-text-secondary">
            Auto
          </label>
        </div>
      </div>
    </div>
  );
};
