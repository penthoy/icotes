/**
 * File Operations Hook
 * 
 * Handles file save, run, close, and activation operations
 */

import { useCallback } from 'react';
import { backendService, ConnectionStatus } from '../../../services';
import { confirmService } from '../../../services/confirmService';
import { EditorFile } from '../types';
import { EditorNotificationService } from '../utils/notifications';
import { EditorView } from '@codemirror/view';

interface UseFileOperationsProps {
  files: EditorFile[];
  setFiles: React.Dispatch<React.SetStateAction<EditorFile[]>>;
  activeFileId: string;
  setActiveFileId: React.Dispatch<React.SetStateAction<string>>;
  connectionStatus: ConnectionStatus;
  editorViewRef: React.RefObject<EditorView | null>;
  onFileSave?: (fileId: string) => void;
  onFileRun?: (fileId: string, content: string, language: string) => void;
  onFileClose?: (fileId: string) => void;
}

export function useFileOperations({
  files,
  setFiles,
  activeFileId,
  setActiveFileId,
  connectionStatus,
  editorViewRef,
  onFileSave,
  onFileRun,
  onFileClose
}: UseFileOperationsProps) {
  
  const handleSaveFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !file.path || !connectionStatus.connected) return;

    try {
      await backendService.saveFile(file.path, file.content);
      
      // Mark file as saved
      setFiles(prevFiles => 
        prevFiles.map(f => 
          f.id === fileId 
            ? { ...f, modified: false }
            : f
        )
      );
      
      EditorNotificationService.show(`Saved ${file.name}`, 'success');
      onFileSave?.(fileId);
    } catch (error) {
      console.error('Failed to save file:', error);
      EditorNotificationService.show(`Failed to save ${file.name}`, 'error');
    }
  }, [files, connectionStatus.connected, setFiles, onFileSave]);

  const handleRunFile = useCallback(async (fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file || !connectionStatus.connected) return;

    try {
      await backendService.executeCode(file.content, file.language, file.path);
      EditorNotificationService.show(`Executed ${file.name}`, 'success');
      onFileRun?.(fileId, file.content, file.language);
    } catch (error) {
      console.error('Failed to execute file:', error);
      EditorNotificationService.show(`Failed to execute ${file.name}`, 'error');
    }
  }, [files, connectionStatus.connected, onFileRun]);

  const handleCloseFile = useCallback((fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (!file) return;

    // Save current editor content before closing if this is the active file
    if (fileId === activeFileId && editorViewRef.current) {
      const currentContent = editorViewRef.current.state.doc.toString();
      if (currentContent !== file.content) {
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === fileId 
              ? { ...f, content: currentContent, modified: f.content !== currentContent }
              : f
          )
        );
        // Update the file object for the confirmation dialog
        Object.assign(file, { content: currentContent, modified: file.content !== currentContent });
      }
    }

    if (file.modified) {
      // Use global confirm dialog
      const shouldSave = confirmService.confirm({ 
        title: 'Unsaved Changes', 
        message: `${file.name} has unsaved changes. Save before closing?`, 
        confirmText: 'Save', 
        cancelText: 'Discard' 
      });
      
      // Handle save choice asynchronously
      (async () => {
        const ok = await shouldSave;
        if (ok && connectionStatus.connected && file.path) {
          await handleSaveFile(fileId);
        }
        // Proceed to close regardless after handling save choice
        setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
        if (fileId === activeFileId) {
          const remainingFiles = files.filter(f => f.id !== fileId);
          if (remainingFiles.length > 0) {
            setActiveFileId(remainingFiles[0].id);
          } else {
            setActiveFileId('');
          }
        }
        onFileClose?.(fileId);
      })();
      return;
    }
    
    // If not modified, proceed to close immediately
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId));
    if (fileId === activeFileId) {
      const remainingFiles = files.filter(f => f.id !== fileId);
      setActiveFileId(remainingFiles[0]?.id || '');
    }
    onFileClose?.(fileId);
  }, [files, activeFileId, connectionStatus.connected, editorViewRef, setFiles, setActiveFileId, onFileClose, handleSaveFile]);

  const handleActivateFile = useCallback(async (fileId: string) => {
    // Save current editor content before switching
    if (activeFileId && editorViewRef.current) {
      const currentContent = editorViewRef.current.state.doc.toString();
      const currentFile = files.find(f => f.id === activeFileId);
      
      if (currentFile && currentContent !== currentFile.content) {
        setFiles(prevFiles => 
          prevFiles.map(f => 
            f.id === activeFileId 
              ? { ...f, content: currentContent, modified: f.content !== currentContent }
              : f
          )
        );
      }
    }
    
    setActiveFileId(fileId);
    onFileSave?.(fileId);
  }, [activeFileId, editorViewRef, files, setFiles, setActiveFileId, onFileSave]);

  return {
    handleSaveFile,
    handleRunFile,
    handleCloseFile,
    handleActivateFile
  };
}
