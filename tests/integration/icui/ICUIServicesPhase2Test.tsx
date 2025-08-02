/**
 * Test implementation for ICUI Phase 5.3 & 5.4 Services
 * Tests File Management Service and Theme Management Service
 */

import React, { useEffect, useState } from 'react';
import { fileService, useTheme } from '../../../src/icui/services';
import type { FileInfo, ThemeInfo } from '../../../src/icui/services';
import { useNotifications } from '../../../src/icui/services/notificationService';

const ICUIServicesPhase2Test: React.FC = () => {
  const { theme, isDark, toggleTheme, switchTheme, getAvailableThemes } = useTheme();
  const notifications = useNotifications();
  // Use the singleton fileService instance
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const [fs] = useState(() => fileService);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [availableThemes, setAvailableThemes] = useState<ThemeInfo[]>([]);
  const [newFileName, setNewFileName] = useState<string>('');
  const [newFileLanguage, setNewFileLanguage] = useState<string>('javascript');

  useEffect(() => {
    // Initialize file service and load available themes
    const initializeServices = async () => {
      try {
        await fileService.initialize();
        const fileList = await fileService.listFiles();
        setFiles(fileList);
        setAvailableThemes(getAvailableThemes());
        notifications.success('Services initialized successfully');
      } catch (error) {
        notifications.error(`Failed to initialize services: ${error.message}`);
      }
    };

    initializeServices();

    // Subscribe to file modifications
    const unsubscribeFileModifications = fileService.onModificationChange((fileId, modified) => {
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, modified } : f
      ));
    });

    return () => {
      unsubscribeFileModifications();
      fileService.destroy();
    };
  }, [fileService, getAvailableThemes, notifications]);

  const handleFileSelect = async (file: FileInfo) => {
    try {
      const fullFile = await fileService.getFile(file.id);
      setSelectedFile(fullFile);
      setFileContent(fullFile.content);
    } catch (error) {
      notifications.error(`Failed to load file: ${error.message}`);
    }
  };

  const handleContentChange = (newContent: string) => {
    if (!selectedFile) return;
    
    setFileContent(newContent);
    const updatedFile = { ...selectedFile, content: newContent, modified: true };
    setSelectedFile(updatedFile);
    
    // Mark as modified and enable auto-save
    fileService.markAsModified(selectedFile.id, true);
    fileService.enableAutoSave(updatedFile, (success) => {
      if (success) {
        setSelectedFile(prev => prev ? { ...prev, modified: false } : null);
      }
    });
  };

  const handleSaveFile = async () => {
    if (!selectedFile) return;
    
    try {
      await fileService.saveFile({ ...selectedFile, content: fileContent });
      setSelectedFile(prev => prev ? { ...prev, modified: false } : null);
      fileService.markAsModified(selectedFile.id, false);
    } catch (error) {
      notifications.error(`Failed to save file: ${error.message}`);
    }
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim()) {
      notifications.warning('Please enter a file name');
      return;
    }
    
    try {
      const newFile = await fileService.createFile(newFileName, newFileLanguage);
      setFiles(prev => [...prev, newFile]);
      setNewFileName('');
      setSelectedFile(newFile);
      setFileContent(newFile.content);
    } catch (error) {
      notifications.error(`Failed to create file: ${error.message}`);
    }
  };

  const handleDeleteFile = async (file: FileInfo) => {
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) return;
    
    try {
      await fileService.deleteFile(file.id);
      setFiles(prev => prev.filter(f => f.id !== file.id));
      if (selectedFile?.id === file.id) {
        setSelectedFile(null);
        setFileContent('');
      }
    } catch (error) {
      notifications.error(`Failed to delete file: ${error.message}`);
    }
  };

  const handleThemeChange = (newTheme: ThemeInfo) => {
    switchTheme(newTheme.cssClass);
  };

  return (
    <div className="p-6 space-y-6 bg-white dark:bg-gray-900 min-h-screen">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
        ICUI Services Test - Phase 5.3 & 5.4
      </h1>

      {/* Theme Management Section */}
      <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
        <h2 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
          Theme Management Service
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-4">
            <span className="text-gray-700 dark:text-gray-300">
              Current Theme: <strong>{theme.name}</strong> ({isDark ? 'Dark' : 'Light'})
            </span>
            <button
              onClick={toggleTheme}
              className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              Toggle Theme
            </button>
          </div>
          
          <div className="flex flex-wrap gap-2">
            <span className="text-gray-700 dark:text-gray-300">Available Themes:</span>
            {availableThemes.map((themeOption) => (
              <button
                key={themeOption.cssClass}
                onClick={() => handleThemeChange(themeOption)}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  theme.cssClass === themeOption.cssClass
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                {themeOption.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* File Management Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* File List */}
        <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <h2 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
            File Management Service
          </h2>
          
          {/* Create New File */}
          <div className="mb-4 p-3 bg-white dark:bg-gray-700 rounded border">
            <h3 className="font-medium mb-2 text-gray-900 dark:text-white">Create New File</h3>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="File name"
                value={newFileName}
                onChange={(e) => setNewFileName(e.target.value)}
                className="w-full px-2 py-1 border rounded text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
              />
              <div className="flex gap-2">
                <select
                  value={newFileLanguage}
                  onChange={(e) => setNewFileLanguage(e.target.value)}
                  className="flex-1 px-2 py-1 border rounded text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                >
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                  <option value="python">Python</option>
                  <option value="html">HTML</option>
                  <option value="css">CSS</option>
                  <option value="markdown">Markdown</option>
                  <option value="json">JSON</option>
                </select>
                <button
                  onClick={handleCreateFile}
                  className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600 transition-colors"
                >
                  Create
                </button>
              </div>
            </div>
          </div>

          {/* File List */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            <h3 className="font-medium text-gray-900 dark:text-white">Files ({files.length})</h3>
            {files.map((file) => (
              <div
                key={file.id}
                className={`p-2 rounded cursor-pointer flex items-center justify-between ${
                  selectedFile?.id === file.id
                    ? 'bg-blue-100 dark:bg-blue-900 border border-blue-300 dark:border-blue-700'
                    : 'bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600'
                }`}
                onClick={() => handleFileSelect(file)}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-xs px-2 py-1 bg-gray-200 dark:bg-gray-600 rounded font-mono">
                    {file.language}
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {file.name}
                    {file.modified && <span className="text-orange-500 ml-1">●</span>}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteFile(file);
                  }}
                  className="text-red-500 hover:text-red-700 text-xs px-2 py-1 rounded hover:bg-red-100 dark:hover:bg-red-900"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* File Editor */}
        <div className="lg:col-span-2 bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              File Editor
            </h2>
            {selectedFile && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedFile.name} {selectedFile.modified && '(modified)'}
                </span>
                <button
                  onClick={handleSaveFile}
                  disabled={!selectedFile.modified}
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    selectedFile.modified
                      ? 'bg-blue-500 text-white hover:bg-blue-600'
                      : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                  }`}
                >
                  Save
                </button>
              </div>
            )}
          </div>

          {selectedFile ? (
            <div className="bg-white dark:bg-gray-900 p-4 rounded border">
              <textarea
                value={fileContent}
                onChange={(e) => handleContentChange(e.target.value)}
                className="w-full h-96 font-mono text-sm p-4 border rounded resize-none text-gray-900 dark:text-white bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
                placeholder="File content..."
              />
              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                Language: {selectedFile.language} | Auto-save: 2s | 
                {selectedFile.modified ? ' Unsaved changes' : ' Saved'}
              </div>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 p-8 rounded border text-center text-gray-500 dark:text-gray-400">
              Select a file to edit
            </div>
          )}
        </div>
      </div>

      {/* Service Features Summary */}
      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
        <h2 className="text-lg font-semibold mb-2 text-blue-900 dark:text-blue-100">
          ICUI Services Framework - Phase 5.3 & 5.4 Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-800 dark:text-blue-200">
          <div>
            <h3 className="font-semibold mb-2">File Management Service (5.3)</h3>
            <ul className="space-y-1">
              <li>✅ File CRUD operations (list, read, create, save, delete)</li>
              <li>✅ Language detection from file extensions</li>
              <li>✅ Auto-save with debouncing (2s delay)</li>
              <li>✅ File modification tracking</li>
              <li>✅ Fallback mode when backend unavailable</li>
              <li>✅ Workspace path management</li>
              <li>✅ Support for 20+ file types and languages</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Theme Management Service (5.4)</h3>
            <ul className="space-y-1">
              <li>✅ Automatic theme detection via MutationObserver</li>
              <li>✅ Support for multiple ICUI themes</li>
              <li>✅ Theme switching and persistence</li>
              <li>✅ React hook integration (`useTheme`)</li>
              <li>✅ CSS variable integration</li>
              <li>✅ Light/Dark theme detection</li>
              <li>✅ Custom theme registration</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ICUIServicesPhase2Test;
