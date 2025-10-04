/**
 * Editor Tab Bar Component
 * 
 * Displays file tabs with close buttons and temporary file indicators
 */

import React from 'react';
import { EditorFile } from '../types';

interface EditorTabBarProps {
  files: EditorFile[];
  activeFileId: string;
  onActivateFile: (fileId: string) => void;
  onCloseFile: (fileId: string) => void;
}

export const EditorTabBar: React.FC<EditorTabBarProps> = ({
  files,
  activeFileId,
  onActivateFile,
  onCloseFile
}) => {
  return (
    <div className="flex border-b icui-tabs">
      {files.map((file) => (
        <div
          key={file.id}
          className={`icui-tab ${file.id === activeFileId ? 'active' : ''}`}
          onClick={() => onActivateFile(file.id)}
          onMouseDown={(e) => {
            // Middle-click (wheel button) to close tab - like VS Code and browsers
            if (e.button === 1) {
              e.preventDefault();
              e.stopPropagation();
              onCloseFile(file.id);
            }
          }}
        >
          <span className={`icui-tab-title ${file.isTemporary ? 'italic' : ''}`}>
            {file.name}
            {file.modified && <span className="ml-1 icui-dot-modified">•</span>}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCloseFile(file.id);
            }}
            className="icui-close-btn"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};
