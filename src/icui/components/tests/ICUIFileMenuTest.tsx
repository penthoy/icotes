/**
 * ICUI File Menu Test Page
 * 
 * Test page for the FileMenu component demonstrating all functionality
 * including file operations, recent files, project management, and integration
 * with the FileService.
 */

import React, { useState, useCallback } from 'react';
import { FileMenu } from '../menus/FileMenu';
import { FileInfo } from '../../services/fileService';
import { notificationService } from '../../services/notificationService';
import '../../styles/FileMenu.css';

// Mock current file data for testing
const mockFiles: FileInfo[] = [
  {
    id: 'file_1',
    name: 'app.js',
    language: 'javascript',
    content: 'console.log("Hello World!");',
    modified: false,
    path: '/project/src/app.js'
  },
  {
    id: 'file_2',
    name: 'styles.css',
    language: 'css',
    content: 'body { margin: 0; }',
    modified: true,
    path: '/project/src/styles.css'
  },
  {
    id: 'file_3',
    name: 'README.md',
    language: 'markdown',
    content: '# My Project\n\nThis is a sample project.',
    modified: false,
    path: '/project/README.md'
  }
];

export const ICUIFileMenuTest: React.FC = () => {
  const [currentFile, setCurrentFile] = useState<FileInfo | undefined>(mockFiles[0]);
  const [openFiles, setOpenFiles] = useState<FileInfo[]>([mockFiles[0]]);
  const [currentProject, setCurrentProject] = useState<string>('/project');

  /**
   * Handle new file creation
   */
  const handleNewFile = useCallback(() => {
    const newFile: FileInfo = {
      id: `file_new_${Date.now()}`,
      name: `untitled_${Date.now()}.js`,
      language: 'javascript',
      content: '',
      modified: false,
      path: `/project/src/untitled_${Date.now()}.js`
    };

    setOpenFiles(prev => [...prev, newFile]);
    setCurrentFile(newFile);
    notificationService.show(`Created new file: ${newFile.name}`, 'success');
  }, []);

  /**
   * Handle file open
   */
  const handleOpenFile = useCallback((file: FileInfo) => {
    if (!openFiles.find(f => f.id === file.id)) {
      setOpenFiles(prev => [...prev, file]);
    }
    setCurrentFile(file);
    notificationService.show(`Opened file: ${file.name}`, 'success');
  }, [openFiles]);

  /**
   * Handle file save
   */
  const handleSaveFile = useCallback((file: FileInfo) => {
    setOpenFiles(prev => 
      prev.map(f => f.id === file.id ? { ...f, modified: false } : f)
    );
    if (currentFile?.id === file.id) {
      setCurrentFile(prev => prev ? { ...prev, modified: false } : prev);
    }
    notificationService.show(`Saved file: ${file.name}`, 'success');
  }, [currentFile]);

  /**
   * Handle save as
   */
  const handleSaveAsFile = useCallback((file: FileInfo) => {
    // Simulate save as dialog
    const newName = prompt('Enter new file name:', file.name);
    if (newName && newName !== file.name) {
      const newFile: FileInfo = {
        ...file,
        id: `file_saveas_${Date.now()}`,
        name: newName,
        path: file.path ? file.path.replace(file.name, newName) : newName,
        modified: false
      };
      
      setOpenFiles(prev => [...prev, newFile]);
      setCurrentFile(newFile);
      notificationService.show(`Saved as: ${newFile.name}`, 'success');
    }
  }, []);

  /**
   * Handle file close
   */
  const handleCloseFile = useCallback((fileId: string) => {
    setOpenFiles(prev => prev.filter(f => f.id !== fileId));
    
    if (currentFile?.id === fileId) {
      const remainingFiles = openFiles.filter(f => f.id !== fileId);
      setCurrentFile(remainingFiles.length > 0 ? remainingFiles[0] : undefined);
    }
    
    const closedFile = openFiles.find(f => f.id === fileId);
    if (closedFile) {
      notificationService.show(`Closed file: ${closedFile.name}`, 'success');
    }
  }, [currentFile, openFiles]);

  /**
   * Handle project open
   */
  const handleOpenProject = useCallback((projectPath: string) => {
    setCurrentProject(projectPath);
    notificationService.show(`Opened project: ${projectPath}`, 'success');
  }, []);

  /**
   * Handle project close
   */
  const handleCloseProject = useCallback(() => {
    setCurrentProject('');
    setOpenFiles([]);
    setCurrentFile(undefined);
    notificationService.show('Closed project', 'success');
  }, []);

  /**
   * Handle settings open
   */
  const handleOpenSettings = useCallback(() => {
    notificationService.show('Settings panel would open here', 'info');
  }, []);

  /**
   * Handle file selection from the test interface
   */
  const handleSelectMockFile = useCallback((file: FileInfo) => {
    setCurrentFile(file);
    if (!openFiles.find(f => f.id === file.id)) {
      setOpenFiles(prev => [...prev, file]);
    }
  }, [openFiles]);

  /**
   * Handle file content change
   */
  const handleContentChange = useCallback((content: string) => {
    if (currentFile) {
      const updatedFile = { ...currentFile, content, modified: true };
      setCurrentFile(updatedFile);
      setOpenFiles(prev => 
        prev.map(f => f.id === currentFile.id ? updatedFile : f)
      );
    }
  }, [currentFile]);

  return (
    <div className="icui-file-menu-test">
      <h1>ICUI File Menu Test</h1>
      
      <div className="test-layout">
        {/* File Menu */}
        <div className="test-section">
          <h2>File Menu</h2>
          <div className="file-menu-container">
            <FileMenu
              currentFile={currentFile}
              onNewFile={handleNewFile}
              onOpenFile={handleOpenFile}
              onSaveFile={handleSaveFile}
              onSaveAsFile={handleSaveAsFile}
              onCloseFile={handleCloseFile}
              onOpenProject={handleOpenProject}
              onCloseProject={handleCloseProject}
              onOpenSettings={handleOpenSettings}
              maxRecentFiles={5}
            />
          </div>
        </div>

        {/* Current State Display */}
        <div className="test-section">
          <h2>Current State</h2>
          
          <div className="state-info">
            <div className="info-item">
              <strong>Current Project:</strong> {currentProject || 'None'}
            </div>
            
            <div className="info-item">
              <strong>Current File:</strong> {currentFile ? `${currentFile.name} (${currentFile.modified ? 'Modified' : 'Saved'})` : 'None'}
            </div>
            
            <div className="info-item">
              <strong>Open Files:</strong> {openFiles.length}
              <ul>
                {openFiles.map(file => (
                  <li key={file.id} className={currentFile?.id === file.id ? 'current' : ''}>
                    {file.name} {file.modified ? '•' : ''}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Mock Files for Testing */}
        <div className="test-section">
          <h2>Test Files</h2>
          <p>Click on these mock files to simulate opening them:</p>
          
          <div className="mock-files">
            {mockFiles.map(file => (
              <button
                key={file.id}
                className={`mock-file-btn ${currentFile?.id === file.id ? 'active' : ''}`}
                onClick={() => handleSelectMockFile(file)}
              >
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
                <span className="file-lang">({file.language})</span>
              </button>
            ))}
          </div>
        </div>

        {/* File Content Editor */}
        {currentFile && (
          <div className="test-section">
            <h2>File Content Editor</h2>
            <div className="editor-info">
              <span>Editing: <strong>{currentFile.name}</strong></span>
              {currentFile.modified && <span className="modified-indicator">• Modified</span>}
            </div>
            
            <textarea
              value={currentFile.content}
              onChange={(e) => handleContentChange(e.target.value)}
              className="content-editor"
              placeholder="File content..."
              rows={10}
            />
          </div>
        )}
      </div>

      <style>{`
        .icui-file-menu-test {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
          font-family: ui-sans-serif, system-ui, sans-serif;
        }

        .test-layout {
          display: grid;
          grid-template-columns: 300px 1fr;
          gap: 20px;
          margin-top: 20px;
        }

        .test-section {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
        }

        .test-section h2 {
          margin: 0 0 12px 0;
          font-size: 16px;
          font-weight: 600;
          color: #111827;
        }

        .file-menu-container {
          display: inline-block;
        }

        .state-info {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .info-item {
          font-size: 14px;
          color: #374151;
        }

        .info-item strong {
          color: #111827;
        }

        .info-item ul {
          margin: 4px 0 0 20px;
          padding: 0;
        }

        .info-item li {
          list-style: disc;
          margin: 2px 0;
        }

        .info-item li.current {
          font-weight: 600;
          color: #3b82f6;
        }

        .mock-files {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .mock-file-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          background: #ffffff;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.15s ease;
        }

        .mock-file-btn:hover {
          background: #f3f4f6;
          border-color: #9ca3af;
        }

        .mock-file-btn.active {
          background: #dbeafe;
          border-color: #3b82f6;
          color: #1e40af;
        }

        .file-icon {
          font-size: 16px;
        }

        .file-name {
          font-weight: 500;
        }

        .file-lang {
          color: #6b7280;
          font-size: 12px;
        }

        .editor-info {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
          padding: 8px 12px;
          background: #f3f4f6;
          border-radius: 6px;
          font-size: 14px;
        }

        .modified-indicator {
          color: #f59e0b;
          font-weight: 600;
        }

        .content-editor {
          width: 100%;
          padding: 12px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-family: ui-monospace, 'Cascadia Code', monospace;
          font-size: 13px;
          line-height: 1.5;
          resize: vertical;
        }

        .content-editor:focus {
          outline: none;
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* Dark theme support */
        [data-theme="dark"] .test-section {
          background: #1f2937;
          border-color: #374151;
        }

        [data-theme="dark"] .test-section h2 {
          color: #f9fafb;
        }

        [data-theme="dark"] .info-item {
          color: #d1d5db;
        }

        [data-theme="dark"] .info-item strong {
          color: #f9fafb;
        }

        [data-theme="dark"] .mock-file-btn {
          background: #374151;
          border-color: #4b5563;
          color: #f9fafb;
        }

        [data-theme="dark"] .mock-file-btn:hover {
          background: #4b5563;
          border-color: #6b7280;
        }

        [data-theme="dark"] .editor-info {
          background: #374151;
          color: #f9fafb;
        }

        [data-theme="dark"] .content-editor {
          background: #374151;
          border-color: #4b5563;
          color: #f9fafb;
        }

        @media (max-width: 768px) {
          .test-layout {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default ICUIFileMenuTest;
