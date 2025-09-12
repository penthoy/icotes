/**
 * ICUI Git Panel Component
 * 
 * Git source control panel similar to VS Code's Source Control view.
 * Provides essential Git workflows: view changes, stage/unstage, commit, and view diffs.
 * 
 * Features:
 * - Repository info (branch, ahead/behind, remotes)
 * - File changes view (staged/unstaged/untracked)
 * - Stage/unstage operations
 * - Commit with message input
 * - Branch operations
 * - Pull/Push operations
 * - Diff preview
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  GitBranch, 
  GitCommit, 
  GitPullRequest,
  Plus, 
  Minus, 
  RotateCcw,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  FileText,
  MoreHorizontal,
  Upload,
  Download,
  Settings
} from "lucide-react";
import { 
  GitFileChange, 
  GitStatus, 
  GitRepoInfo, 
  GitBranches,
  GIT_STATUS_CONFIG,
  GitStatusType 
} from '../../types/git-types';
import { backendService } from '../../services';
import { confirmService } from '../../services/confirmService';
import { getWorkspaceRoot } from '../../lib/workspaceUtils';
import { Button } from '../ui/button';
import { useTheme } from '../../services';
import { log } from '../../../services/frontend-logger';
import ICUIGitConnect from '../ICUIGitConnect';

interface ICUIGitProps {
  className?: string;
  onFileSelect?: (path: string) => void;
  onFileOpen?: (file: { type: string; path: string; name: string }) => void;
  onOpenDiffPatch?: (path: string) => void; // Phase 4 integration: open diff in editor
  onGitRepoStatusChange?: (hasRepo: boolean) => void; // Callback for repo status changes
}

const ICUIGit: React.FC<ICUIGitProps> = ({
  className = '',
  onFileSelect,
  onFileOpen,
  onOpenDiffPatch,
  onGitRepoStatusChange,
}) => {
  // State management
  const [repoInfo, setRepoInfo] = useState<GitRepoInfo | null>(null);
  const [status, setStatus] = useState<GitStatus>({ staged: [], unstaged: [], untracked: [] });
  const [branches, setBranches] = useState<GitBranches>({ current: '', local: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  // Simple repo state machine: unknown (initial), present, absent
  const [repoState, setRepoState] = useState<'unknown' | 'present' | 'absent'>('unknown');
  // Phase 3 additions
  const [showBranchInput, setShowBranchInput] = useState(false);
  const [newBranchName, setNewBranchName] = useState('');
  const [commitHistory, setCommitHistory] = useState<string[]>([]); // recent commit messages
  const [showCommitHistory, setShowCommitHistory] = useState(false);
  const [commitTemplate, setCommitTemplate] = useState('');
  
  // UI state
  const [expandedSections, setExpandedSections] = useState({
    changes: true,
    staged: true
  });
  const [commitMessage, setCommitMessage] = useState('');
  const [commitOptions, setCommitOptions] = useState({
    amend: false,
    signoff: false
  });
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  // Removed legacy diffPreview modal state – diffs always open in editor tabs now
  const [contextMenu, setContextMenu] = useState<{
    x: number; y: number; file: GitFileChange; isStaged: boolean;
  } | null>(null);

  // Commit templates (simple conventional commit prefixes)
  const COMMIT_TEMPLATES = useMemo(() => [
    'feat: ',
    'fix: ',
    'chore: ',
    'docs: ',
    'refactor: ',
    'test: ',
    'perf: '
  ], []);
  
  // Refs
  const commitTextareaRef = useRef<HTMLTextAreaElement>(null);
  const refreshTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const { theme } = useTheme();

  // ==================== Data Loading ====================
  
  const loadRepoInfo = useCallback(async (): Promise<boolean> => {
    try {
      const info = await backendService.getScmRepoInfo();
      const present = !!(info && (info.branch || info.root || info.repoPath));
      if (present) {
        setRepoInfo(info);
        setIsConnected(true);
        setRepoState('present');
        onGitRepoStatusChange?.(true);
      } else {
        setRepoInfo(null);
        setIsConnected(false);
        setRepoState('absent');
        onGitRepoStatusChange?.(false);
      }
      return present;
    } catch (error) {
      console.warn('[ICUIGit] Failed to load repo info:', error);
      setRepoInfo(null);
      setIsConnected(false);
      setRepoState('absent');
      onGitRepoStatusChange?.(false);
      return false;
    }
  }, [onGitRepoStatusChange]);

  // Decide if we should render the connect component (only when clearly no repo)
  const testMode = import.meta.env.VITE_TEST_GIT_CONNECT === 'true';
  const showConnect = useMemo(() => (testMode || repoState === 'absent'), [repoState, testMode]);

  const loadStatus = useCallback(async () => {
    try {
      const statusData = await backendService.getScmStatus();
      setStatus(statusData);
      setError(null);
    } catch (error) {
      // If no repo, backend may error – only log at debug level
      console.warn('[ICUIGit] loadStatus warning:', error);
      setError(prev => prev || (error instanceof Error ? error.message : 'Failed to load Git status'));
    }
  }, []);

  const loadBranches = useCallback(async () => {
    try {
      const branchData = await backendService.getScmBranches();
      setBranches(branchData);
    } catch (error) {
      console.warn('[ICUIGit] Failed to load branches:', error);
    }
  }, []);

  const loadAll = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const present = await loadRepoInfo();
      if (present) {
        await Promise.all([
          loadBranches(),
          loadStatus()
        ]);
      } else {
        // Ensure status lists are empty when no repo
        setStatus({ staged: [], unstaged: [], untracked: [] });
      }
    } catch (error) {
      log.error('[ICUIGit] Failed to load Git data:', error);
    } finally {
      setLoading(false);
    }
  }, [loading, loadRepoInfo, loadBranches, loadStatus]);

  // Initial load
  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Subscribe to backend SCM websocket events (scm.status_changed, scm.branch_changed)
  useEffect(() => {
    // backendService may expose an EventEmitter API
    try {
      const onStatus = () => loadStatus();
      const onBranch = () => { loadRepoInfo(); loadBranches(); };
      
      backendService.on?.('scm.status_changed', onStatus);
      backendService.on?.('scm.branch_changed', onBranch);
      
      return () => {
        try { 
          backendService.off?.('scm.status_changed', onStatus); 
          backendService.off?.('scm.branch_changed', onBranch); 
        } catch (_) { /* ignore */ }
      };
    } catch (_) { 
      /* ignore if EventEmitter methods don't exist */
      return () => {};
    }
  }, [loadStatus, loadRepoInfo, loadBranches]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) loadStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, [loading, loadStatus]);

  // ==================== File Operations ====================
  
  const handleStage = useCallback(async (paths: string[]) => {
    try {
      setLoading(true);
      const success = await backendService.scmStage(paths);
      if (success) {
        await loadStatus();
        setSelectedFiles(new Set());
      } else {
        setError('Failed to stage files');
      }
    } catch (error) {
      console.error('[ICUIGit] Stage failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to stage files');
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const handleUnstage = useCallback(async (paths: string[]) => {
    try {
      setLoading(true);
      const success = await backendService.scmUnstage(paths);
      if (success) {
        await loadStatus();
        setSelectedFiles(new Set());
      } else {
        setError('Failed to unstage files');
      }
    } catch (error) {
      console.error('[ICUIGit] Unstage failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to unstage files');
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const handleDeleteUntracked = useCallback(async (paths: string[]) => {
    try {
      const ok = await confirmService.confirm({
        title: paths.length === 1 ? 'Delete File' : 'Delete Files',
        message: `Delete ${paths.length} untracked file(s)? This cannot be undone.`,
        danger: true,
        confirmText: 'Delete'
      });
      if (!ok) return;

      setLoading(true);
      for (const relativePath of paths) {
        try {
          // Resolve relative Git path to absolute path
          const absolutePath = resolveGitFilePath(relativePath);
          console.log('[ICUIGit] Deleting untracked file:', relativePath, '->', absolutePath);
          await backendService.deleteFile(absolutePath);
        } catch (e) {
          console.warn('[ICUIGit] Failed deleting untracked file', relativePath, e);
        }
      }
      await loadStatus();
      setSelectedFiles(new Set());
    } catch (error) {
      console.error('[ICUIGit] Delete untracked failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to delete untracked files');
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const handleDiscard = useCallback(async (paths: string[]) => {
    try {
      const ok = await confirmService.confirm({
        title: paths.length === 1 ? 'Discard Changes' : 'Discard Multiple Changes',
        message: `Discard changes to ${paths.length} file(s)? This cannot be undone.`,
        danger: true,
        confirmText: 'Discard'
      });
      if (!ok) return;
      setLoading(true);
      const success = await backendService.scmDiscard(paths);
      if (success) {
        await loadStatus();
        setSelectedFiles(new Set());
      } else {
        setError('Failed to discard changes');
      }
    } catch (error) {
      console.error('[ICUIGit] Discard failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to discard changes');
    } finally {
      setLoading(false);
    }
  }, [loadStatus]);

  const handleCommit = useCallback(async () => {
    const message = commitMessage.trim();
    if (!message) {
      setError('Commit message is required');
      return;
    }

    // Auto-stage if user has only unstaged/untracked changes
    const needsAutoStage = status.staged.length === 0 && (status.unstaged.length > 0 || status.untracked.length > 0);
    const pathsToStage = needsAutoStage ? [...status.unstaged.map(f => f.path), ...status.untracked.map(f => f.path)] : [];

    try {
      setLoading(true);
      if (needsAutoStage && pathsToStage.length > 0) {
        const staged = await backendService.scmStage(pathsToStage);
        if (!staged) {
          setError('Failed to auto-stage changes before commit');
          setLoading(false);
          return;
        }
        await loadStatus();
      }

      const success = await backendService.scmCommit(
        message,
        commitOptions.amend,
        commitOptions.signoff
      );
      
      if (success) {
        // update recent history (dedupe, cap 10)
        setCommitHistory(prev => {
          const next = [message, ...prev.filter(m => m !== message)];
            return next.slice(0, 10);
        });
        setCommitMessage('');
        setCommitOptions({ amend: false, signoff: false });
        setCommitTemplate('');
        await loadAll();
      } else {
        setError('Failed to commit changes');
      }
    } catch (error) {
      console.error('[ICUIGit] Commit failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to commit changes');
    } finally {
      setLoading(false);
    }
  }, [commitMessage, commitOptions, status.staged.length, status.unstaged.length, status.untracked.length, loadAll, loadStatus]);

  // ==================== Branch Operations ====================
  
  const handleCheckout = useCallback(async (branch: string) => {
    try {
      setLoading(true);
      const success = await backendService.scmCheckout(branch);
      if (success) {
        await loadAll();
      } else {
        setError(`Failed to checkout branch: ${branch}`);
      }
    } catch (error) {
      console.error('[ICUIGit] Checkout failed:', error);
      setError(error instanceof Error ? error.message : `Failed to checkout branch: ${branch}`);
    } finally {
      setLoading(false);
    }
  }, [loadAll]);

  const handlePull = useCallback(async () => {
    try {
      setLoading(true);
      const success = await backendService.scmPull();
      if (success) {
        await loadAll();
      } else {
        setError('Failed to pull from remote');
      }
    } catch (error) {
      console.error('[ICUIGit] Pull failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to pull from remote');
    } finally {
      setLoading(false);
    }
  }, [loadAll]);

  const handlePush = useCallback(async (setUpstream: boolean = false) => {
    try {
      setLoading(true);
      const success = await backendService.scmPush(setUpstream);
      if (success) {
        await loadAll();
      } else {
        setError('Failed to push to remote');
      }
    } catch (error) {
      console.error('[ICUIGit] Push failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to push to remote');
    } finally {
      setLoading(false);
    }
  }, [loadAll]);

  // Create branch (Phase 3 addition)
  const handleCreateBranch = useCallback(async () => {
    const name = newBranchName.trim();
    if (!name) return;
    try {
      setLoading(true);
      const success = await backendService.scmCheckout(name, true);
      if (!success) {
        setError(`Failed to create branch ${name}`);
        return;
      }
      setShowBranchInput(false);
      setNewBranchName('');
      await loadAll();
    } catch (error) {
      console.error('[ICUIGit] Create branch failed:', error);
      setError(error instanceof Error ? error.message : `Failed to create branch ${name}`);
    } finally {
      setLoading(false);
    }
  }, [newBranchName, loadAll]);

  // ==================== Diff Preview ====================
  
  // Helper function to resolve git file paths correctly (moved outside useCallback to avoid dependency issues)
  const resolveGitFilePath = useCallback((filePath: string): string => {
    // If it's already an absolute path, use it
  if (filePath.startsWith('/')) return filePath;
    
    // Prefer server-reported Git root; fallback to workspace root
  const baseRoot = (repoInfo?.root || getWorkspaceRoot());
  return `${baseRoot.replace(/\/+$/, '')}/${filePath.replace(/^\/+/, '')}`;
  }, [repoInfo?.root]);

  const handleShowDiff = useCallback(async (path: string) => {
    // Convert Git relative path to absolute path for diff
  const absolutePath = resolveGitFilePath(path);
    
    // For untracked files, create a synthetic diff showing the entire file as added
    const file = [...status.unstaged, ...status.untracked, ...status.staged].find(f => f.path === path);
    if (file && file.status === '?') {
      try {
        // Load file content and create a synthetic "added" diff
        const content = await backendService.readFile(absolutePath);
        const lines = content.split('\n');
        const syntheticPatch = [
          `diff --git a/${path} b/${path}`,
          'new file mode 100644',
          'index 0000000..1234567',
          `--- /dev/null`,
          `+++ b/${path}`,
          `@@ -0,0 +1,${lines.length} @@`,
          ...lines.map(line => `+${line}`)
        ].join('\n');
        
        // Dispatch synthetic diff event with absolute path
        window.dispatchEvent(new CustomEvent('icui:openSyntheticDiff', { 
          detail: { path: absolutePath, patch: syntheticPatch } 
        }));
        return;
      } catch (error) {
        console.warn('[ICUIGit] Failed to create synthetic diff for untracked file:', error);
        // Fall through to normal diff handling
      }
    }
    
    if (onOpenDiffPatch) {
      onOpenDiffPatch(absolutePath);
      return;
    }
    // Fallback: dispatch global event only (no modal)
    try {
      window.dispatchEvent(new CustomEvent('icui:openDiffPatch', { detail: { path: absolutePath } }));
    } catch (e) {
      console.warn('[ICUIGit] Global diff event dispatch failed:', e);
    }
  }, [onOpenDiffPatch, status.unstaged, status.untracked, status.staged, resolveGitFilePath]);

  // ==================== UI Helpers ====================
  
  const toggleSection = useCallback((section: 'changes' | 'staged') => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  }, []);

  const allUnstagedFiles = useMemo(() => 
    [...status.unstaged, ...status.untracked],
    [status.unstaged, status.untracked]
  );

  const hasAnyChanges = useMemo(() => (
    status.staged.length + status.unstaged.length + status.untracked.length
  ) > 0, [status.staged.length, status.unstaged.length, status.untracked.length]);

  const canCommit = useMemo(() => 
    hasAnyChanges && commitMessage.trim().length > 0,
    [hasAnyChanges, commitMessage]
  );

  const totalChanges = useMemo(() => 
    status.staged.length + status.unstaged.length + status.untracked.length,
    [status.staged.length, status.unstaged.length, status.untracked.length]
  );

  // ==================== File List Components ====================
  
  const FileItem: React.FC<{ 
    file: GitFileChange;
    isStaged: boolean;
    onShowDiff: () => void;
  }> = ({ file, isStaged, onShowDiff }) => {
    const statusConfig = GIT_STATUS_CONFIG[file.status as GitStatusType] || GIT_STATUS_CONFIG['?'];
    const filename = file.path.split('/').pop() || file.path;
    const dir = file.path.slice(0, file.path.length - filename.length).replace(/\/$/, '');
    return (
      <div
        className="flex items-center justify-between px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 group cursor-pointer"
        onClick={onShowDiff}
        onContextMenu={(e) => {
          e.preventDefault();
          setContextMenu({ x: e.clientX, y: e.clientY, file, isStaged });
        }}
        title={`View diff for ${file.path}`}
      >
        <div className="flex items-start space-x-2 flex-1 min-w-0">
          <span className={`text-xs font-mono mt-0.5 ${statusConfig.color}`}>{statusConfig.icon}</span>
          <div className="flex flex-col min-w-0 leading-tight">
            <span className="text-sm truncate font-medium">{filename}</span>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate" title={file.path}>{dir || '.'}</span>
          </div>
        </div>
      </div>
    );
  };

  // ==================== Render ====================
  
  if (showConnect) {
    return (
      <ICUIGitConnect
        className={className}
        onGitInitialized={async () => {
          const present = await loadRepoInfo();
            if (present) {
              await Promise.all([loadBranches(), loadStatus()]);
            }
        }}
      />
    );
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center space-x-2">
          <GitBranch className="h-4 w-4" />
          <h3 className="text-sm font-medium">Source Control</h3>
          {totalChanges > 0 && (
            <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded-full">
              {totalChanges}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={loadAll}
            title="Refresh"
            className="h-6 w-6 p-0"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            title="More actions"
            className="h-6 w-6 p-0"
          >
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-2 bg-red-50 border-b border-red-200 dark:bg-red-900/20 dark:border-red-800">
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setError(null)}
            className="ml-2 h-4 w-4 p-0 text-red-600 dark:text-red-400"
          >
            ✕
          </Button>
        </div>
      )}

      {/* Repository Info */}
      {repoInfo && (
        <div className="p-3 border-b bg-gray-50 dark:bg-gray-800">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <GitBranch className="h-4 w-4" />
              <span className="text-sm font-medium">{repoInfo.branch}</span>
              {(repoInfo.ahead > 0 || repoInfo.behind > 0) && (
                <span className="text-xs text-gray-500">
                  {repoInfo.ahead > 0 && `↑${repoInfo.ahead}`}
                  {repoInfo.behind > 0 && `↓${repoInfo.behind}`}
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-1">
              <div className="relative">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handlePull}
                  title={repoInfo.behind > 0 ? `Pull (${repoInfo.behind} behind)` : 'Pull'}
                  className="h-6 w-6 p-0"
                  disabled={loading || repoInfo.behind === 0}
                >
                  <Download className="h-3 w-3" />
                </Button>
                {repoInfo.behind > 0 && (
                  <span className="absolute -top-1 -right-1 bg-blue-500 text-white rounded-full text-[10px] px-1 leading-tight">
                    {repoInfo.behind}
                  </span>
                )}
              </div>
              <div className="relative">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handlePush()}
                  title={repoInfo.ahead > 0 ? `Push (${repoInfo.ahead} ahead)` : 'Push'}
                  className="h-6 w-6 p-0"
                  disabled={loading || repoInfo.ahead === 0}
                >
                  <Upload className="h-3 w-3" />
                </Button>
                {repoInfo.ahead > 0 && (
                  <span className="absolute -top-1 -right-1 bg-green-600 text-white rounded-full text-[10px] px-1 leading-tight">
                    {repoInfo.ahead}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {showBranchInput && (
            <div className="mt-2 flex items-center space-x-2">
              <input
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                placeholder="new-branch-name"
                className="flex-1 text-xs px-2 py-1 border rounded dark:bg-gray-700"
              />
              <Button size="sm" onClick={handleCreateBranch} disabled={!newBranchName.trim() || loading} className="h-6 px-2 text-xs">Create</Button>
            </div>
          )}
          {/* Remote URL removed to avoid exposing credentials/PAT. Branch name shown above is sufficient. */}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Changes Section - hide entirely if empty */}
        {allUnstagedFiles.length > 0 && (
          <div className="border-b">
            <button
              onClick={() => toggleSection('changes')}
              className="w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <div className="flex items-center space-x-2">
                {expandedSections.changes ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <span className="text-sm font-medium">
                  Changes ({allUnstagedFiles.length})
                </span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  handleStage(allUnstagedFiles.map(f => f.path));
                }}
                title="Stage all changes"
                className="h-6 w-6 p-0"
              >
                <Plus className="h-3 w-3" />
              </Button>
            </button>
            {expandedSections.changes && (
              <div className="pb-2">
                {allUnstagedFiles.map((file) => (
                  <FileItem
                    key={file.path}
                    file={file}
                    isStaged={false}
                    onShowDiff={() => handleShowDiff(file.path)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Staged Changes Section - hide entirely if empty */}
        {status.staged.length > 0 && (
          <div className="border-b">
            <button
              onClick={() => toggleSection('staged')}
              className="w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <div className="flex items-center space-x-2">
                {expandedSections.staged ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <span className="text-sm font-medium">
                  Staged Changes ({status.staged.length})
                </span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  handleUnstage(status.staged.map(f => f.path));
                }}
                title="Unstage all changes"
                className="h-6 w-6 p-0"
              >
                <Minus className="h-3 w-3" />
              </Button>
            </button>
            {expandedSections.staged && (
              <div className="pb-2">
                {status.staged.map((file) => (
                  <FileItem
                    key={file.path}
                    file={file}
                    isStaged={true}
                    onShowDiff={() => handleShowDiff(file.path)}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Commit Section */}
      <div className="p-3 border-t bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center justify-between mb-1">
          <select
            value={commitTemplate}
            onChange={(e) => {
              const val = e.target.value;
              setCommitTemplate(val);
              if (val && !commitMessage.startsWith(val)) {
                setCommitMessage(prev => `${val}${prev}`);
              }
            }}
            className="text-xs border rounded px-1 py-0.5 dark:bg-gray-700"
          >
            <option value="">template</option>
            {COMMIT_TEMPLATES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-xs"
            onClick={() => setShowCommitHistory(s => !s)}
            title="Show recent commit messages"
          >hist</Button>
        </div>
        <textarea
          ref={commitTextareaRef}
          value={commitMessage}
          onChange={(e) => setCommitMessage(e.target.value)}
          placeholder="Commit message"
          rows={3}
          className="w-full p-2 text-sm border rounded resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
        />
        {showCommitHistory && commitHistory.length > 0 && (
          <div className="mt-2 border rounded bg-white dark:bg-gray-700 max-h-32 overflow-auto">
            {commitHistory.map(msg => (
              <button
                key={msg}
                onClick={() => { setCommitMessage(msg); setShowCommitHistory(false); }}
                className="block w-full text-left px-2 py-1 text-xs hover:bg-gray-100 dark:hover:bg-gray-600 truncate"
                title={msg}
              >{msg}</button>
            ))}
          </div>
        )}
        
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center space-x-2 text-xs">
            <label className="flex items-center space-x-1">
              <input
                type="checkbox"
                checked={commitOptions.amend}
                onChange={(e) => setCommitOptions(prev => ({ 
                  ...prev, 
                  amend: e.target.checked 
                }))}
                className="rounded"
              />
              <span>Amend</span>
            </label>
            
            <label className="flex items-center space-x-1">
              <input
                type="checkbox"
                checked={commitOptions.signoff}
                onChange={(e) => setCommitOptions(prev => ({ 
                  ...prev, 
                  signoff: e.target.checked 
                }))}
                className="rounded"
              />
              <span>Sign-off</span>
            </label>
          </div>
          
          <Button
            size="sm"
            onClick={handleCommit}
            disabled={!canCommit || loading}
            title={!hasAnyChanges ? 'No changes to commit' : (commitMessage.trim().length === 0 ? 'Enter a commit message' : (loading ? 'Working...' : 'Commit changes'))}
            className="flex items-center space-x-1"
          >
            <GitCommit className="h-3 w-3" />
            <span>Commit</span>
          </Button>
        </div>
      </div>

  {/* Legacy diff modal removed: diffs now always open as editor tabs */}
      {contextMenu && (
        <div
          className="fixed inset-0 z-50"
          onClick={() => setContextMenu(null)}
          onContextMenu={(e) => { e.preventDefault(); setContextMenu(null); }}
        >
          <div
            className="absolute bg-white dark:bg-gray-800 border dark:border-gray-700 rounded shadow-lg py-1 text-sm min-w-[180px]"
            style={{ top: contextMenu.y, left: contextMenu.x }}
            role="menu"
          >
            {/* Stage / Unstage */}
            {!contextMenu.isStaged && (
              <button
                className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                onClick={() => { handleStage([contextMenu.file.path]); setContextMenu(null); }}
              >
                <Plus className="h-3 w-3" /> <span>Stage</span>
              </button>
            )}
            {contextMenu.isStaged && (
              <button
                className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                onClick={() => { handleUnstage([contextMenu.file.path]); setContextMenu(null); }}
              >
                <Minus className="h-3 w-3" /> <span>Unstage</span>
              </button>
            )}
            {/* Discard for modified tracked files */}
            {!contextMenu.isStaged && contextMenu.file.status !== '?' && (
              <button
                className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                onClick={() => { handleDiscard([contextMenu.file.path]); setContextMenu(null); }}
              >
                <RotateCcw className="h-3 w-3" /> <span>Discard Changes</span>
              </button>
            )}
            {/* Delete untracked file */}
            {!contextMenu.isStaged && contextMenu.file.status === '?' && (
              <button
                className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                onClick={() => { handleDeleteUntracked([contextMenu.file.path]); setContextMenu(null); }}
              >
                <RotateCcw className="h-3 w-3" /> <span>Delete File</span>
              </button>
            )}
            <div className="h-px my-1 bg-gray-200 dark:bg-gray-700" />
            {/* Open File */}
            <button
              className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
              onClick={() => { 
                if (onFileOpen) {
                  // Convert Git relative path to absolute path
                  const absolutePath = resolveGitFilePath(contextMenu.file.path);
                  // Opening file from Git panel
                  
                  // Create file object that matches ICUIFileNode interface (like Explorer)
                  const fileNode = { 
                    id: `git-file-${contextMenu.file.path}`, // Add unique ID
                    type: 'file' as const, 
                    path: absolutePath, 
                    name: contextMenu.file.path.split('/').pop() || contextMenu.file.path 
                  };
                  
                  onFileOpen(fileNode); 
                } else {
                  console.error('[ICUIGit] onFileOpen callback is not available');
                }
                setContextMenu(null); 
              }}
            >
              <FileText className="h-3 w-3" /> <span>Open File</span>
            </button>
            {/* Diff (explicit option) */}
            <button
              className="w-full text-left px-3 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
              onClick={() => { handleShowDiff(contextMenu.file.path); setContextMenu(null); }}
            >
              <span className="text-xs font-mono">Δ</span> <span>Open Diff</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ICUIGit;
