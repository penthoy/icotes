import { Command, CommandUtils, globalCommandRegistry } from '../../lib/commandRegistry';
import { backendService, ICUIFileNode } from '../../services';
import { log } from '../../../services/frontend-logger';
import { confirmService } from '../../services/confirmService';
import { promptService } from '../../services/promptService';
import { getRelativeWorkspacePath } from '../../lib/workspaceUtils';
import { copyToClipboard } from '../../utils/clipboardUtils';

export interface FileOperationContext {
  selectedFiles: ICUIFileNode[];
  currentPath: string;
  refreshDirectory: () => Promise<void>;
  onFileCreate?: (path: string) => void;
  onFolderCreate?: (path: string) => void;
  onFileDelete?: (path: string) => void;
  onFileRename?: (oldPath: string, newPath: string) => void;
  /**
   * When invoking a command from a context menu on a specific folder, this path
   * represents the intended parent directory for creation commands.
   * Falls back to currentPath when not provided.
   */
  targetDirectoryPath?: string;
}

/**
 * Explorer File Operations Manager
 */
export class ExplorerFileOperations {
  private static instance: ExplorerFileOperations | null = null;
  private clipboard: { operation: 'copy' | 'cut'; files: ICUIFileNode[] } | null = null;
  // Track whether commands have been registered to avoid duplicate registrations
  private registered = false;

  static getInstance(): ExplorerFileOperations {
    if (!ExplorerFileOperations.instance) {
      ExplorerFileOperations.instance = new ExplorerFileOperations();
    }
    return ExplorerFileOperations.instance;
  }

  /**
   * Register all file operation commands
   */
  registerCommands(): void {
    if (this.registered) {
      // Avoid noisy duplicate registrations during HMR or remounts
      log.debug('ExplorerFileOperations', 'registerCommands skipped (already registered)');
      return;
    }
    const commands: Command[] = [
      // File/Folder Creation
      CommandUtils.createWithShortcut(
        'explorer.newFile',
        'New File',
        'Ctrl+N',
        this.createNewFile.bind(this),
        { 
          category: 'file',
          icon: '📄',
          description: 'Create a new file in the current directory'
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.newFolder',
        'New Folder',
        'Ctrl+Shift+N',
        this.createNewFolder.bind(this),
        { 
          category: 'file',
          icon: '📁',
          description: 'Create a new folder in the current directory'
        }
      ),

      // File Operations
      CommandUtils.createWithShortcut(
        'explorer.rename',
        'Rename',
        'F2',
        this.renameFile.bind(this),
        { 
          category: 'file',
          icon: '✏️',
          description: 'Rename the selected file or folder'
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.delete',
        'Delete',
        'Delete',
        this.deleteFiles.bind(this),
        { 
          category: 'file',
          icon: '🗑️',
          description: 'Delete the selected files or folders',
          // Mark as dangerous action for confirmation
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.duplicate',
        'Duplicate',
        'Ctrl+D',
        this.duplicateFiles.bind(this),
        { 
          category: 'file',
          icon: '📋',
          description: 'Duplicate the selected files or folders'
        }
      ),

      // Clipboard Operations
      CommandUtils.createWithShortcut(
        'explorer.copy',
        'Copy',
        'Ctrl+C',
        this.copyFiles.bind(this),
        { 
          category: 'edit',
          icon: '📋',
          description: 'Copy the selected files or folders'
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.cut',
        'Cut',
        'Ctrl+X',
        this.cutFiles.bind(this),
        { 
          category: 'edit',
          icon: '✂️',
          description: 'Cut the selected files or folders'
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.paste',
        'Paste',
        'Ctrl+V',
        this.pasteFiles.bind(this),
        { 
          category: 'edit',
          icon: '📄',
          description: 'Paste files or folders from clipboard'
        }
      ),

      // Navigation
      CommandUtils.createWithShortcut(
        'explorer.refresh',
        'Refresh',
        'F5',
        this.refreshDirectory.bind(this),
        { 
          category: 'view',
          icon: '🔄',
          description: 'Refresh the current directory'
        }
      ),

      // Download (Phase 5)
      CommandUtils.create(
        'explorer.download',
        'Download',
        this.downloadFiles.bind(this),
        { 
          category: 'file',
          icon: '⬇️',
          description: 'Download the selected files or folders'
        }
      ),
      // Cross-context send (copy) operation
      CommandUtils.create(
        'explorer.sendTo',
        'Send To (Context)',
        this.sendToContext.bind(this),
        {
          category: 'integration',
          icon: '📨',
          description: 'Send selected files/folders to another hop context default workspace path'
        }
      ),

      // Copy path operations
      CommandUtils.createWithShortcut(
        'explorer.copyPath',
        'Copy Path',
        'Ctrl+Shift+C',
        this.copyPath.bind(this),
        {
          category: 'edit',
          icon: '📋',
          description: 'Copy the absolute path of the selected file'
        }
      ),

      CommandUtils.createWithShortcut(
        'explorer.copyRelativePath',
        'Copy Relative Path',
        'Ctrl+Shift+Alt+C',
        this.copyRelativePath.bind(this),
        {
          category: 'edit',
          icon: '📋',
          description: 'Copy the relative path of the selected file'
        }
      ),

      // Preview command
      CommandUtils.create(
        'explorer.preview',
        'Preview',
        this.previewFile.bind(this),
        {
          category: 'view',
          icon: '👁️',
          description: 'Preview file in Preview panel'
        }
      ),
    ];

    commands.forEach(command => {
      globalCommandRegistry.register(command);
    });

    log.info('ExplorerFileOperations', 'Registered file operation commands', { count: commands.length });
    this.registered = true;
  }

  /**
   * Unregister all file operation commands
   */
  unregisterCommands(): void {
    if (!this.registered) {
      return; // Nothing to do
    }
    const commandIds = [
      'explorer.newFile',
      'explorer.newFolder',
      'explorer.copy',
      'explorer.cut',
      'explorer.paste',
      'explorer.delete',
      'explorer.duplicate',
      'explorer.rename',
      // selection actions are not registered via command registry here
      'explorer.refresh',
      'explorer.download',
      'explorer.sendTo',
      'explorer.copyPath',
      'explorer.copyRelativePath',
      'explorer.preview',
    ];

    commandIds.forEach(commandId => {
      globalCommandRegistry.unregister(commandId);
    });

    log.info('ExplorerFileOperations', 'Unregistered file operation commands');
    this.registered = false;
  }

  /**
   * Create a new file in the current directory
   */
  private async createNewFile(context?: FileOperationContext): Promise<void> {
    if (!context) {
      log.warn('ExplorerFileOperations', 'createNewFile called without context');
      return;
    }

    const fileName = await promptService.prompt({ title: 'New File', message: 'Enter file name:', placeholder: 'example.txt' });
    if (!fileName || !fileName.trim()) return;

    const trimmed = fileName.trim();
    let baseDir = (context.targetDirectoryPath || context.currentPath || '/').replace(/\/+$/, '');
    if (baseDir === '') baseDir = '/';

    if (trimmed.includes('..')) {
      await confirmService.confirm({
        title: 'Invalid Name',
        message: 'The file name contains an invalid path sequence (..).',
        confirmText: 'OK',
        cancelText: 'Cancel'
      });
      return;
    }

    try {
      const siblings = await backendService.getDirectoryContents(baseDir, true).catch(() => [] as ICUIFileNode[]);
      const conflict = siblings.find(s => s.name === trimmed);
      if (conflict) {
        await confirmService.confirm({
          title: 'Name Conflict',
          message: `A ${conflict.type === 'folder' ? 'folder' : 'file'} named "${trimmed}" already exists here.`,
          confirmText: 'OK',
          cancelText: 'Cancel'
        });
        return;
      }
    } catch (e) {
      log.warn('ExplorerFileOperations', 'Directory listing failed during collision check', { baseDir, error: e });
    }

    const newPath = `${baseDir}/${trimmed}`.replace(/\/+/g, '/');

    try {
      await backendService.createFile(newPath);
      // Skipping manual refresh to rely on filesystem event emission
      log.debug('ExplorerFileOperations', 'Skipped manual refresh after file create; waiting for filesystem event', { path: newPath });
      context.onFileCreate?.(newPath);
      log.info('ExplorerFileOperations', 'Created new file', { path: newPath });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to create file', { path: newPath, error });
      throw error;
    }
  }

  private async createNewFolder(context?: FileOperationContext): Promise<void> {
    if (!context) {
      log.warn('ExplorerFileOperations', 'createNewFolder called without context');
      return;
    }

    const folderName = await promptService.prompt({ title: 'New Folder', message: 'Enter folder name:', placeholder: 'my-folder' });
    if (!folderName || !folderName.trim()) return;
    const trimmed = folderName.trim();

    // Defensive resolution of base directory
    let baseDirRaw = (context.targetDirectoryPath || context.currentPath || '/');
    baseDirRaw = baseDirRaw.replace(/\\/g, '/').replace(/\/+$/, '');
    if (baseDirRaw === '') baseDirRaw = '/';
    if (context.selectedFiles.length === 1 && context.selectedFiles[0].type === 'file' && context.selectedFiles[0].path === baseDirRaw) {
      baseDirRaw = baseDirRaw.includes('/') ? (baseDirRaw.substring(0, baseDirRaw.lastIndexOf('/')) || '/') : '/';
    }
    const baseDir = baseDirRaw;

    if (trimmed.includes('..')) {
      await confirmService.confirm({
        title: 'Invalid Name',
        message: 'The folder name contains an invalid path sequence (..).',
        confirmText: 'OK',
        cancelText: 'Cancel'
      });
      return;
    }

    try {
      const siblings = await backendService.getDirectoryContents(baseDir, true).catch(() => [] as ICUIFileNode[]);
      const conflict = siblings.find(s => s.name === trimmed);
      if (conflict) {
        await confirmService.confirm({
          title: 'Name Conflict',
          message: `A ${conflict.type === 'folder' ? 'folder' : 'file'} named "${trimmed}" already exists here.`,
          confirmText: 'OK',
          cancelText: 'Cancel'
        });
        return;
      }
    } catch (e) {
      log.warn('ExplorerFileOperations', 'Directory listing failed during folder collision check', { baseDir, error: e });
    }

    const newPath = `${baseDir}/${trimmed}`.replace(/\\/g, '/').replace(/\/+/, '/');
    log.debug('ExplorerFileOperations', 'Creating folder', { baseDir, newPath });
    try {
      await backendService.createDirectory(newPath);
      // NOTE: Intentionally skipping immediate manual refresh to avoid double refresh.
      // The backend emits an fs.directory_created event which the Explorer listens for
      // and triggers a (debounced) refresh. Previously we refreshed here AND from the
      // event handler, causing two rapid refreshes and visible flicker. If for some
      // reason the event does not arrive, we can add a fallback timer-based refresh.
      log.debug('ExplorerFileOperations', 'Skipped manual refresh; waiting for filesystem event', { newPath });
      context.onFolderCreate?.(newPath);
      log.info('ExplorerFileOperations', 'Created new folder', { path: newPath });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to create folder', { path: newPath, error });
      throw error;
    }
  }

  private async renameFile(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length !== 1) {
      log.warn('ExplorerFileOperations', 'renameFile requires exactly one selected file');
      return;
    }
    const file = context.selectedFiles[0];
    const newName = await promptService.prompt({ title: 'Rename', message: 'Enter new name:', initialValue: file.name });
    if (!newName || !newName.trim() || newName.trim() === file.name) return;
    const parentPath = file.path.substring(0, file.path.lastIndexOf('/'));
    const newPath = `${parentPath}/${newName.trim()}`.replace(/\/+/, '/');
    try {
      if (file.type === 'file') {
        const content = await backendService.readFile(file.path);
        await backendService.createFile(newPath, content);
        await backendService.deleteFile(file.path);
      } else {
        await backendService.createDirectory(newPath);
        await backendService.deleteFile(file.path);
      }
      // Rely on create/delete filesystem events instead of manual refresh
      log.debug('ExplorerFileOperations', 'Skipped manual refresh after rename; waiting for filesystem events', { oldPath: file.path, newPath });
      context.onFileRename?.(file.path, newPath);
      log.info('ExplorerFileOperations', 'Renamed file', { oldPath: file.path, newPath });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to rename file', { oldPath: file.path, newPath, error });
      throw error;
    }
  }

  /**
   * Delete selected files and folders
   */
  private async deleteFiles(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'deleteFiles called with no selected files');
      return;
    }

    const fileNames = context.selectedFiles.map(f => f.name).join(', ');
    const confirmMessage = context.selectedFiles.length === 1
      ? `Are you sure you want to delete "${fileNames}"?`
      : `Are you sure you want to delete ${context.selectedFiles.length} items?`;

  const ok = await confirmService.confirm({ title: 'Delete Items', message: confirmMessage, danger: true, confirmText: 'Delete' });
  if (!ok) {
      return;
    }

    try {
      // Delete all selected files
      await Promise.all(
        context.selectedFiles.map(file => backendService.deleteFile(file.path))
      );
      // Deletion events will trigger explorer refresh via watcher
      log.debug('ExplorerFileOperations', 'Skipped manual refresh after deletions; waiting for filesystem events', { count: context.selectedFiles.length });
      
      // Notify about deletions
      context.selectedFiles.forEach(file => {
        context.onFileDelete?.(file.path);
      });

      log.info('ExplorerFileOperations', 'Deleted files', { 
        count: context.selectedFiles.length,
        paths: context.selectedFiles.map(f => f.path)
      });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to delete files', { 
        files: context.selectedFiles.map(f => f.path),
        error 
      });
      throw error;
    }
  }

  /**
   * Duplicate selected files and folders
   */
  private async duplicateFiles(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'duplicateFiles called with no selected files');
      return;
    }

    try {
      for (const file of context.selectedFiles) {
        const extension = file.name.includes('.') ? `.${file.name.split('.').pop()}` : '';
        const baseName = file.name.replace(new RegExp(`${extension}$`), '');
        const newName = `${baseName}_copy${extension}`;
        const newPath = `${file.path.substring(0, file.path.lastIndexOf('/'))}/${newName}`.replace(/\/+/g, '/');

        if (file.type === 'file') {
          // For files, read content and create new file
          const content = await backendService.readFile(file.path);
          await backendService.createFile(newPath, content);
        } else {
          // For directories, use backend copy operation if available
          // This is a simplified implementation - a full solution would recursively copy
          await backendService.createDirectory(newPath);
        }
      }

      // Duplicate operations create new entries; rely on watcher events
      log.debug('ExplorerFileOperations', 'Skipped manual refresh after duplicate; waiting for filesystem events', { count: context.selectedFiles.length });
      log.info('ExplorerFileOperations', 'Duplicated files', { 
        count: context.selectedFiles.length 
      });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to duplicate files', { 
        files: context.selectedFiles.map(f => f.path),
        error 
      });
      throw error;
    }
  }

  /**
   * Copy files to clipboard
   */
  private async copyFiles(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'copyFiles called with no selected files');
      return;
    }

    this.clipboard = {
      operation: 'copy',
      files: [...context.selectedFiles],
    };

    log.info('ExplorerFileOperations', 'Copied files to clipboard', { 
      count: context.selectedFiles.length 
    });
  }

  /**
   * Cut files to clipboard
   */
  private async cutFiles(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'cutFiles called with no selected files');
      return;
    }

    this.clipboard = {
      operation: 'cut',
      files: [...context.selectedFiles],
    };

    log.info('ExplorerFileOperations', 'Cut files to clipboard', { 
      count: context.selectedFiles.length 
    });
  }

  /**
   * Paste files from clipboard
   */
  private async pasteFiles(context?: FileOperationContext): Promise<void> {
    if (!context || !this.clipboard) {
      log.warn('ExplorerFileOperations', 'pasteFiles called without context or clipboard');
      return;
    }

    try {
      for (const file of this.clipboard.files) {
        const fileName = file.name;
        const newPath = `${context.currentPath}/${fileName}`.replace(/\/+/g, '/');

        if (this.clipboard.operation === 'copy') {
          if (file.type === 'file') {
            const content = await backendService.readFile(file.path);
            await backendService.createFile(newPath, content);
          } else {
            await backendService.createDirectory(newPath);
          }
        } else if (this.clipboard.operation === 'cut') {
          // For cut operation, create new location and delete old
          if (file.type === 'file') {
            const content = await backendService.readFile(file.path);
            await backendService.createFile(newPath, content);
            await backendService.deleteFile(file.path);
          } else {
            await backendService.createDirectory(newPath);
            await backendService.deleteFile(file.path);
          }
        }
      }

      // Clear clipboard after cut operation
      if (this.clipboard.operation === 'cut') {
        this.clipboard = null;
      }

      // Paste (copy/cut) results in creates (and maybe deletes) -> rely on watcher events
      log.debug('ExplorerFileOperations', 'Skipped manual refresh after paste; waiting for filesystem events', { operation: this.clipboard?.operation });
      log.info('ExplorerFileOperations', 'Pasted files', { 
        operation: this.clipboard?.operation,
        count: this.clipboard?.files.length
      });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to paste files', { 
        operation: this.clipboard?.operation,
        files: this.clipboard?.files.map(f => f.path),
        error 
      });
      throw error;
    }
  }

  /**
   * Send selected files/folders to a target hop context (copy semantics)
   * Triggered via context menu submenu items with args.targetContextId
   */
  private async sendToContext(context?: FileOperationContext & { args?: any }): Promise<void> {
    if (!context) {
      log.warn('ExplorerFileOperations', 'sendToContext called without context');
      return;
    }
    const targetContextId = (context as any).args?.targetContextId;
    if (!targetContextId) {
      log.warn('ExplorerFileOperations', 'sendToContext missing targetContextId');
      await confirmService.confirm({
        title: 'Send Failed',
        message: 'Target context not specified',
        confirmText: 'OK'
      });
      return;
    }
    if (!context.selectedFiles || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'sendToContext no selected files');
      return;
    }
    try {
      const itemCount = context.selectedFiles.length;
      const itemLabel = itemCount === 1 ? context.selectedFiles[0].name : `${itemCount} items`;
      
      // Show sending notification
      log.info('ExplorerFileOperations', `Sending ${itemLabel} to ${targetContextId}...`);
      
      // Derive a common prefix so relative structure is preserved
      const paths = context.selectedFiles.map(f => f.path);
      const commonPrefix = this.computeCommonPrefix(paths);
      
      // @ts-ignore dynamic method exists on enhanced backendService
      const result = await (backendService as any).sendFilesToContext(targetContextId, paths, { commonPrefix });
      
      const createdCount = result?.created?.length || 0;
      const errorCount = result?.errors?.length || 0;
      
      if (errorCount > 0) {
        const errorDetails = result?.errors?.slice(0, 3).join('\n') || 'Unknown errors';
        const moreErrors = errorCount > 3 ? `\n... and ${errorCount - 3} more` : '';
        await confirmService.confirm({
          title: 'Send Completed with Errors',
          message: `Sent ${createdCount} items to ${targetContextId}, but ${errorCount} failed:\n\n${errorDetails}${moreErrors}`,
          confirmText: 'OK'
        });
      } else {
        await confirmService.confirm({
          title: 'Send Complete',
          message: `Successfully sent ${itemLabel} to ${targetContextId}`,
          confirmText: 'OK'
        });
      }
      
      log.info('ExplorerFileOperations', 'sendToContext result', { targetContextId, created: createdCount, errors: errorCount });
      
      // Optionally refresh the current directory to reflect any changes
      if (context.refreshDirectory) {
        await context.refreshDirectory();
      }
    } catch (error: any) {
      log.error('ExplorerFileOperations', 'Failed to send files to context', { error });
      await confirmService.confirm({
        title: 'Send Failed',
        message: error?.message || 'Failed to send files to target context',
        confirmText: 'OK'
      });
    }
  }

  private computeCommonPrefix(paths: string[]): string | null {
    if (paths.length === 0) return null;
    
    // For a single file, return its parent directory
    if (paths.length === 1) {
      const path = paths[0];
      const lastSlash = path.lastIndexOf('/');
      if (lastSlash <= 0) return null; // Root or no slash
      return path.substring(0, lastSlash);
    }
    
    // For multiple files, find common prefix
    const splitPaths = paths.map(p => p.split('/').filter(Boolean));
    const first = splitPaths[0];
    let prefix: string[] = [];
    for (let i = 0; i < first.length; i++) {
      const segment = first[i];
      if (splitPaths.every(parts => parts[i] === segment)) {
        prefix.push(segment);
      } else {
        break;
      }
    }
    if (prefix.length === 0) return null;
    return '/' + prefix.join('/');
  }

  /**
   * Refresh the current directory
   */
  private async refreshDirectory(context?: FileOperationContext): Promise<void> {
    if (!context) {
      log.warn('ExplorerFileOperations', 'refreshDirectory called without context');
      return;
    }

    await context.refreshDirectory();
    log.info('ExplorerFileOperations', 'Refreshed directory', { path: context.currentPath });
  }

  /**
   * Copy absolute path to clipboard
   */
  private async copyPath(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length !== 1) {
      log.warn('ExplorerFileOperations', 'copyPath requires exactly one selected file');
      return;
    }

    const file = context.selectedFiles[0];
    try {
      await copyToClipboard(file.path);
      log.info('ExplorerFileOperations', 'Copied absolute path to clipboard', { path: file.path });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to copy path to clipboard', { path: file.path, error });
      await confirmService.confirm({
        title: 'Copy Failed',
        message: `Failed to copy path to clipboard: ${error instanceof Error ? error.message : 'Unknown error'}`,
        confirmText: 'OK'
      });
    }
  }

  /**
   * Copy relative path to clipboard
   */
  private async copyRelativePath(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length !== 1) {
      log.warn('ExplorerFileOperations', 'copyRelativePath requires exactly one selected file');
      return;
    }

    const file = context.selectedFiles[0];
    const relativePath = getRelativeWorkspacePath(file.path);

    try {
      await copyToClipboard(relativePath);
      log.info('ExplorerFileOperations', 'Copied relative path to clipboard', { 
        absolutePath: file.path,
        relativePath 
      });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to copy relative path to clipboard', { 
        path: file.path, 
        error 
      });
      await confirmService.confirm({
        title: 'Copy Failed',
        message: `Failed to copy relative path to clipboard: ${error instanceof Error ? error.message : 'Unknown error'}`,
        confirmText: 'OK'
      });
    }
  }



  /**
   * Download selected files (Phase 5)
   */
  private async downloadFiles(context?: FileOperationContext): Promise<void> {
    if (!context || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'downloadFiles requires selected files');
      return;
    }

    try {
      if (context.selectedFiles.length === 1) {
        // Single file download
        const file = context.selectedFiles[0];
        const url = `/api/files/download?path=${encodeURIComponent(file.path)}`;
        
        // Create temporary download link
        const link = document.createElement('a');
        link.href = url;
        link.download = file.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        log.info('ExplorerFileOperations', 'Downloaded single file', { path: file.path });
      } else {
        // Multiple files - create zip
        const paths = context.selectedFiles.map(f => f.path);
        
        const response = await fetch('/api/media/zip', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paths }),
        });

        if (!response.ok) {
          throw new Error(`Zip creation failed: ${response.statusText}`);
        }

        // Download the zip
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `files-${Date.now()}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);

        log.info('ExplorerFileOperations', 'Downloaded multiple files as zip', { 
          count: context.selectedFiles.length,
          paths 
        });
      }
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to download files', { 
        files: context.selectedFiles.map(f => f.path),
        error 
      });
      throw error;
    }
  }

  /**
   * Preview file in Preview panel
   */
  private async previewFile(context?: FileOperationContext): Promise<void> {
    if (!context || !context.selectedFiles || context.selectedFiles.length === 0) {
      log.warn('ExplorerFileOperations', 'previewFile requires a selected file');
      return;
    }

    const file = context.selectedFiles[0];
    log.info('ExplorerFileOperations', 'Opening file in preview panel', { path: file.path });

    try {
      // Read main file content
      // Extract namespace and path (format: "namespace:/path" or just "/path")
      let cleanPath = file.path;
      let namespace = 'local';
      
      const namespaceMatch = file.path.match(/^([^:]+):(.+)$/);
      if (namespaceMatch) {
        namespace = namespaceMatch[1];
        cleanPath = namespaceMatch[2];
      }
      
      const response = await fetch(`/api/files/content?path=${encodeURIComponent(cleanPath)}&namespace=${namespace}`);
      if (!response.ok) {
        throw new Error(`Failed to read file: ${response.statusText}`);
      }
      
      const data = await response.json();
      const content = data.data?.content || data.content || '';
      
      // Create files object starting with the main file
      const files: Record<string, string> = {
        [file.name]: content
      };
      
      // Calculate directory path for asset loading
      let dirPath = file.path;
      if (dirPath.includes(':/')) {
        dirPath = dirPath.substring(dirPath.indexOf(':/') + 1);
      }
      if (dirPath.includes('/')) {
        const lastSlashIndex = dirPath.lastIndexOf('/');
        dirPath = lastSlashIndex === 0 ? '/' : dirPath.substring(0, lastSlashIndex);
      } else {
        dirPath = '/';
      }
      if (!dirPath) dirPath = '/';
      
      // For HTML files, try to find and include related files in the same directory
      if (file.name.endsWith('.html') || file.name.endsWith('.htm')) {
        
        // List files in the same directory using /api/files
        try {
          // Use the namespace from the original file
          const dirResponse = await fetch(`/api/files?path=${encodeURIComponent(namespace + ':' + dirPath)}&include_hidden=false`);
          if (dirResponse.ok) {
            const dirData = await dirResponse.json();
            // Backend returns file list under data ("data") not children; keep backward compatibility
            const dirFiles = dirData.children || dirData.data || dirData.files || [];
            
            // Use both console + log.debug so it appears in aggregated logs
            console.log('[FileOperations] Directory files:', dirFiles.map((f: any) => f.name));
            try {
              (log as any).debug?.('ExplorerFileOperations', 'Preview directory listing', { path: dirPath, files: dirFiles.map((f: any) => f.name) });
            } catch (_) {}
            
            // Look for common web asset files
            const assetExtensions = ['.css', '.js', '.json', '.svg', '.png', '.jpg', '.jpeg', '.gif'];
            const relatedFiles = dirFiles.filter((f: any) => 
              !f.is_directory && 
              assetExtensions.some(ext => f.name.toLowerCase().endsWith(ext))
            );
            
            // Read and include related files
            for (const relFile of relatedFiles) {
              try {
                // Extract namespace and clean path from file path
                let relCleanPath = relFile.path;
                let relNamespace = namespace;
                const relMatch = relFile.path.match(/^([^:]+):(.+)$/);
                if (relMatch) {
                  relNamespace = relMatch[1];
                  relCleanPath = relMatch[2];
                }
                
                const relResponse = await fetch(`/api/files/content?path=${encodeURIComponent(relCleanPath)}&namespace=${relNamespace}`);
                if (relResponse.ok) {
                  const relData = await relResponse.json();
                  files[relFile.name] = relData.data?.content || relData.content || '';
                }
              } catch (err) {
                log.warn('ExplorerFileOperations', 'Error reading related file', { file: relFile.name, error: err });
              }
            }

            // Fallback: Parse HTML for <link>/<script> references if no assets were included
            if (Object.keys(files).length === 1) {
              try {
                
                const parser = new DOMParser();
                const doc = parser.parseFromString(content, 'text/html');
                
                const links = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
                const scripts = Array.from(doc.querySelectorAll('script[src]'));
                
                const foundAssetPaths = [
                  ...links.map(l => l.getAttribute('href')),
                  ...scripts.map(s => s.getAttribute('src'))
                ].filter((path): path is string => !!path);

                for (const assetRef of foundAssetPaths) {
                  // Skip remote URLs
                  if (/^(https?:|\/\/)/i.test(assetRef)) {
                    continue;
                  }
                  
                  let assetPath = assetRef.startsWith('./') ? assetRef.substring(2) : assetRef;
                  assetPath = assetPath.split('?')[0].split('#')[0];
                  const fullPath = (dirPath.endsWith('/') ? dirPath : dirPath + '/') + assetPath;
                  
                  try {
                    const assetResp = await fetch(`/api/files/content?path=${encodeURIComponent(fullPath)}&namespace=${namespace}`);
                    if (assetResp.ok) {
                      const assetData = await assetResp.json();
                      const assetName = assetPath.split('/').pop() || assetPath;
                      files[assetName] = assetData.data?.content || assetData.content || '';
                    }
                  } catch (err) {
                    log.debug('ExplorerFileOperations', 'Fallback asset read failed', { asset: assetRef, error: err });
                  }
                }
              } catch (fallbackErr) {
                log.warn('ExplorerFileOperations', 'Fallback asset parsing failed', { error: fallbackErr });
              }
            }
          } else {
            log.warn('ExplorerFileOperations', 'Failed to list directory', { status: dirResponse.status });
          }
        } catch (err) {
          log.warn('ExplorerFileOperations', 'Failed to list directory for related files', { error: err });
        }
      }
      
      // Dispatch custom event to trigger preview
      window.dispatchEvent(new CustomEvent('icui:preview', {
        detail: { files, baseDir: dirPath }
      }));
      
      log.info('ExplorerFileOperations', 'Preview event dispatched', { file: file.name, totalFiles: Object.keys(files).length });
    } catch (error) {
      log.error('ExplorerFileOperations', 'Failed to preview file', { 
        path: file.path,
        error 
      });
      console.error('[FileOperations] Preview failed:', error);
      await confirmService.confirm({
        title: 'Preview Failed',
        message: error instanceof Error ? error.message : 'Failed to preview file',
        confirmText: 'OK'
      });
    }
  }

  /**
   * Check if paste operation is available
   */
  canPaste(): boolean {
    return this.clipboard !== null;
  }

  /**
   * Get clipboard status for UI feedback
   */
  getClipboardStatus(): { operation: 'copy' | 'cut'; count: number } | null {
    if (!this.clipboard) return null;
    
    return {
      operation: this.clipboard.operation,
      count: this.clipboard.files.length,
    };
  }
}

/**
 * Get the singleton instance
 */
export const explorerFileOperations = ExplorerFileOperations.getInstance();
