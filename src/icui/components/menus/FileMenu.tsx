/**
 * ICUI File Menu Component
 * 
 * Dedicated file operations menu component for the ICUI framework.
 * Provides file operations (New, Open, Save, Close), recent files list,
 * and project management functionality as specified in icui_plan.md 6.2.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { FileService, FileInfo } from '../../services/fileService';
import { notificationService } from '../../services/notificationService';

export interface RecentFile {
  id: string;
  name: string;
  path: string;
  lastAccessed: Date;
}

export interface FileMenuProps {
  currentFile?: FileInfo;
  onNewFile?: () => void;
  onOpenFile?: (file: FileInfo) => void;
  onSaveFile?: (file: FileInfo) => void;
  onSaveAsFile?: (file: FileInfo) => void;
  onCloseFile?: (fileId: string) => void;
  onOpenProject?: (projectPath: string) => void;
  onCloseProject?: () => void;
  onOpenSettings?: () => void;
  className?: string;
  maxRecentFiles?: number;
}

export interface Project {
  name: string;
  path: string;
  lastOpened: Date;
}

/**
 * File Menu Component
 * 
 * Provides comprehensive file management operations including:
 * - File CRUD operations (New, Open, Save, Save As, Close)
 * - Recent files tracking and management
 * - Project management (Open Project, Close Project)
 * - Settings access
 */
export const FileMenu: React.FC<FileMenuProps> = ({
  currentFile,
  onNewFile,
  onOpenFile,
  onSaveFile,
  onSaveAsFile,
  onCloseFile,
  onOpenProject,
  onCloseProject,
  onOpenSettings,
  className = '',
  maxRecentFiles = 10
}) => {
  const [fileService] = useState(() => new FileService());
  const [recentFiles, setRecentFiles] = useState<RecentFile[]>([]);
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Load recent files and projects from localStorage on mount
   */
  useEffect(() => {
    loadRecentFiles();
    loadRecentProjects();
  }, []);

  /**
   * Load recent files from localStorage
   */
  const loadRecentFiles = useCallback(() => {
    try {
      const stored = localStorage.getItem('icui-recent-files');
      if (stored) {
        const parsed = JSON.parse(stored);
        setRecentFiles(parsed.map((item: any) => ({
          ...item,
          lastAccessed: new Date(item.lastAccessed)
        })));
      }
    } catch (error) {
      console.warn('Failed to load recent files:', error);
    }
  }, []);

  /**
   * Load recent projects from localStorage
   */
  const loadRecentProjects = useCallback(() => {
    try {
      const stored = localStorage.getItem('icui-recent-projects');
      if (stored) {
        const parsed = JSON.parse(stored);
        setRecentProjects(parsed.map((item: any) => ({
          ...item,
          lastOpened: new Date(item.lastOpened)
        })));
      }
    } catch (error) {
      console.warn('Failed to load recent projects:', error);
    }
  }, []);

  /**
   * Add file to recent files list
   */
  const addToRecentFiles = useCallback((file: FileInfo) => {
    setRecentFiles(prev => {
      const existing = prev.findIndex(f => f.id === file.id);
      const recentFile: RecentFile = {
        id: file.id,
        name: file.name,
        path: file.path || '',
        lastAccessed: new Date()
      };

      let updated;
      if (existing >= 0) {
        // Move to top if already exists
        updated = [recentFile, ...prev.filter((_, i) => i !== existing)];
      } else {
        // Add new file to top
        updated = [recentFile, ...prev.slice(0, maxRecentFiles - 1)];
      }

      // Save to localStorage
      try {
        localStorage.setItem('icui-recent-files', JSON.stringify(updated));
      } catch (error) {
        console.warn('Failed to save recent files:', error);
      }

      return updated;
    });
  }, [maxRecentFiles]);

  /**
   * Add project to recent projects list
   */
  const addToRecentProjects = useCallback((project: Omit<Project, 'lastOpened'>) => {
    setRecentProjects(prev => {
      const existing = prev.findIndex(p => p.path === project.path);
      const recentProject: Project = {
        ...project,
        lastOpened: new Date()
      };

      let updated;
      if (existing >= 0) {
        // Move to top if already exists
        updated = [recentProject, ...prev.filter((_, i) => i !== existing)];
      } else {
        // Add new project to top
        updated = [recentProject, ...prev.slice(0, 4)]; // Keep max 5 recent projects
      }

      // Save to localStorage
      try {
        localStorage.setItem('icui-recent-projects', JSON.stringify(updated));
      } catch (error) {
        console.warn('Failed to save recent projects:', error);
      }

      return updated;
    });
  }, []);

  /**
   * Handle new file creation
   */
  const handleNewFile = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // Create file using service with proper parameters
      const newFile = await fileService.createFile('untitled', 'javascript', '');
      
      onNewFile?.();
      notificationService.show('New file created', 'success');
      
    } catch (error) {
      console.error('Failed to create new file:', error);
      notificationService.show('Failed to create new file', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [fileService, onNewFile]);

  /**
   * Handle file open from dialog
   */
  const handleOpenFile = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // In a real implementation, this would open a file dialog
      // For now, we'll simulate or delegate to parent component
      // The actual file picking logic would depend on the environment
      
      notificationService.show('File open dialog would appear here', 'info');
      
    } catch (error) {
      console.error('Failed to open file:', error);
      notificationService.show('Failed to open file', 'error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Handle opening a recent file
   */
  const handleOpenRecentFile = useCallback(async (recentFile: RecentFile) => {
    try {
      setIsLoading(true);
      
      // Load file using service (using getFile method)
      const file = await fileService.getFile(recentFile.id);
      
      if (file) {
        addToRecentFiles(file);
        onOpenFile?.(file);
        notificationService.show(`Opened ${file.name}`, 'success');
      } else {
        notificationService.show('File not found or could not be loaded', 'error');
      }
      
    } catch (error) {
      console.error('Failed to open recent file:', error);
      notificationService.show('Failed to open recent file', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [fileService, onOpenFile, addToRecentFiles]);

  /**
   * Handle file save
   */
  const handleSaveFile = useCallback(async () => {
    if (!currentFile) {
      notificationService.show('No file to save', 'warning');
      return;
    }

    try {
      setIsLoading(true);
      
      await fileService.saveFile(currentFile, false);
      addToRecentFiles(currentFile);
      onSaveFile?.(currentFile);
      
    } catch (error) {
      console.error('Failed to save file:', error);
      notificationService.show('Failed to save file', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [currentFile, fileService, onSaveFile, addToRecentFiles]);

  /**
   * Handle save as
   */
  const handleSaveAsFile = useCallback(async () => {
    if (!currentFile) {
      notificationService.show('No file to save', 'warning');
      return;
    }

    try {
      setIsLoading(true);
      
      // In a real implementation, this would open a save dialog
      // For now, we'll delegate to parent component
      onSaveAsFile?.(currentFile);
      notificationService.show('Save As dialog would appear here', 'info');
      
    } catch (error) {
      console.error('Failed to save file as:', error);
      notificationService.show('Failed to save file as', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [currentFile, onSaveAsFile]);

  /**
   * Handle file close
   */
  const handleCloseFile = useCallback(() => {
    if (!currentFile) {
      notificationService.show('No file to close', 'warning');
      return;
    }

    if (currentFile.modified) {
      // In a real implementation, show save confirmation dialog
      if (window.confirm(`Save changes to ${currentFile.name}?`)) {
        handleSaveFile().then(() => {
          onCloseFile?.(currentFile.id);
        });
        return;
      }
    }

    onCloseFile?.(currentFile.id);
    notificationService.show(`Closed ${currentFile.name}`, 'success');
  }, [currentFile, onCloseFile, handleSaveFile]);

  /**
   * Handle project open
   */
  const handleOpenProject = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // In a real implementation, this would open a folder dialog
      // For now, we'll simulate or delegate to parent component
      notificationService.show('Project open dialog would appear here', 'info');
      
    } catch (error) {
      console.error('Failed to open project:', error);
      notificationService.show('Failed to open project', 'error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Handle opening a recent project
   */
  const handleOpenRecentProject = useCallback(async (project: Project) => {
    try {
      setIsLoading(true);
      
      addToRecentProjects(project);
      onOpenProject?.(project.path);
      notificationService.show(`Opened project ${project.name}`, 'success');
      
    } catch (error) {
      console.error('Failed to open recent project:', error);
      notificationService.show('Failed to open recent project', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [onOpenProject, addToRecentProjects]);

  /**
   * Handle project close
   */
  const handleCloseProject = useCallback(() => {
    onCloseProject?.();
    notificationService.show('Project closed', 'success');
  }, [onCloseProject]);

  /**
   * Clear recent files
   */
  const handleClearRecentFiles = useCallback(() => {
    setRecentFiles([]);
    localStorage.removeItem('icui-recent-files');
    notificationService.show('Recent files cleared', 'success');
  }, []);

  /**
   * Clear recent projects
   */
  const handleClearRecentProjects = useCallback(() => {
    setRecentProjects([]);
    localStorage.removeItem('icui-recent-projects');
    notificationService.show('Recent projects cleared', 'success');
  }, []);

  return (
    <div className={`icui-file-menu ${className}`}>
      {/* File Operations Section */}
      <div className="icui-file-menu-section">
        <h3 className="icui-file-menu-section-title">File</h3>
        
        <button
          className="icui-file-menu-item"
          onClick={handleNewFile}
          disabled={isLoading}
          title="Create a new file (Ctrl+N)"
        >
          <span className="icui-file-menu-icon">📄</span>
          New File
          <span className="icui-file-menu-shortcut">Ctrl+N</span>
        </button>

        <button
          className="icui-file-menu-item"
          onClick={handleOpenFile}
          disabled={isLoading}
          title="Open a file (Ctrl+O)"
        >
          <span className="icui-file-menu-icon">📁</span>
          Open...
          <span className="icui-file-menu-shortcut">Ctrl+O</span>
        </button>

        <div className="icui-file-menu-separator" />

        <button
          className="icui-file-menu-item"
          onClick={handleSaveFile}
          disabled={isLoading || !currentFile}
          title="Save current file (Ctrl+S)"
        >
          <span className="icui-file-menu-icon">💾</span>
          Save
          <span className="icui-file-menu-shortcut">Ctrl+S</span>
        </button>

        <button
          className="icui-file-menu-item"
          onClick={handleSaveAsFile}
          disabled={isLoading || !currentFile}
          title="Save file with new name (Ctrl+Shift+S)"
        >
          <span className="icui-file-menu-icon">💾</span>
          Save As...
          <span className="icui-file-menu-shortcut">Ctrl+Shift+S</span>
        </button>

        <div className="icui-file-menu-separator" />

        <button
          className="icui-file-menu-item"
          onClick={handleCloseFile}
          disabled={isLoading || !currentFile}
          title="Close current file (Ctrl+W)"
        >
          <span className="icui-file-menu-icon">✖️</span>
          Close File
          <span className="icui-file-menu-shortcut">Ctrl+W</span>
        </button>
      </div>

      {/* Recent Files Section */}
      {recentFiles.length > 0 && (
        <div className="icui-file-menu-section">
          <div className="icui-file-menu-section-header">
            <h3 className="icui-file-menu-section-title">Recent Files</h3>
            <button
              className="icui-file-menu-clear-btn"
              onClick={handleClearRecentFiles}
              title="Clear recent files"
            >
              Clear
            </button>
          </div>
          
          {recentFiles.slice(0, maxRecentFiles).map((file, index) => (
            <button
              key={file.id}
              className="icui-file-menu-item icui-file-menu-recent-item"
              onClick={() => handleOpenRecentFile(file)}
              disabled={isLoading}
              title={`Open ${file.name} (${file.path})`}
            >
              <span className="icui-file-menu-icon">📄</span>
              <span className="icui-file-menu-recent-info">
                <span className="icui-file-menu-recent-name">{file.name}</span>
                <span className="icui-file-menu-recent-path">{file.path}</span>
              </span>
              <span className="icui-file-menu-recent-number">{index + 1}</span>
            </button>
          ))}
        </div>
      )}

      {/* Project Management Section */}
      <div className="icui-file-menu-section">
        <h3 className="icui-file-menu-section-title">Project</h3>
        
        <button
          className="icui-file-menu-item"
          onClick={handleOpenProject}
          disabled={isLoading}
          title="Open a project folder"
        >
          <span className="icui-file-menu-icon">📂</span>
          Open Project...
        </button>

        <button
          className="icui-file-menu-item"
          onClick={handleCloseProject}
          disabled={isLoading}
          title="Close current project"
        >
          <span className="icui-file-menu-icon">📂</span>
          Close Project
        </button>
      </div>

      {/* Recent Projects Section */}
      {recentProjects.length > 0 && (
        <div className="icui-file-menu-section">
          <div className="icui-file-menu-section-header">
            <h3 className="icui-file-menu-section-title">Recent Projects</h3>
            <button
              className="icui-file-menu-clear-btn"
              onClick={handleClearRecentProjects}
              title="Clear recent projects"
            >
              Clear
            </button>
          </div>
          
          {recentProjects.slice(0, 5).map((project, index) => (
            <button
              key={project.path}
              className="icui-file-menu-item icui-file-menu-recent-item"
              onClick={() => handleOpenRecentProject(project)}
              disabled={isLoading}
              title={`Open project ${project.name} (${project.path})`}
            >
              <span className="icui-file-menu-icon">📂</span>
              <span className="icui-file-menu-recent-info">
                <span className="icui-file-menu-recent-name">{project.name}</span>
                <span className="icui-file-menu-recent-path">{project.path}</span>
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Settings Section */}
      <div className="icui-file-menu-section">
        <div className="icui-file-menu-separator" />
        
        <button
          className="icui-file-menu-item"
          onClick={onOpenSettings}
          disabled={isLoading}
          title="Open settings"
        >
          <span className="icui-file-menu-icon">⚙️</span>
          Settings
        </button>
      </div>
    </div>
  );
};

export default FileMenu;
