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
  Eye,
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
import { Button } from '../ui/button';
import { useTheme } from '../../services';
import { log } from '../../../services/frontend-logger';

interface ICUIGitProps {
  className?: string;
  onFileSelect?: (path: string) => void;
  onFileOpen?: (path: string) => void;
  onOpenDiffPatch?: (path: string) => void; // Phase 4 integration: open diff in editor
}

const ICUIGit: React.FC<ICUIGitProps> = ({
  className = '',
  onFileSelect,
  onFileOpen,
  onOpenDiffPatch,
}) => {
  // State management
  const [repoInfo, setRepoInfo] = useState<GitRepoInfo | null>(null);
  const [status, setStatus] = useState<GitStatus>({ staged: [], unstaged: [], untracked: [] });
  const [branches, setBranches] = useState<GitBranches>({ current: '', local: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
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
  
  const loadRepoInfo = useCallback(async () => {
    try {
      const info = await backendService.getScmRepoInfo();
      setRepoInfo(info);
      setIsConnected(true);
    } catch (error) {
      console.warn('[ICUIGit] Failed to load repo info:', error);
      setRepoInfo(null);
      setIsConnected(false);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const statusData = await backendService.getScmStatus();
      setStatus(statusData);
      setError(null);
    } catch (error) {
      console.error('[ICUIGit] Failed to load status:', error);
      setError(error instanceof Error ? error.message : 'Failed to load Git status');
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
      await Promise.all([
        loadRepoInfo(),
        loadStatus(),
        loadBranches()
      ]);
    } catch (error) {
      log.error('[ICUIGit] Failed to load Git data:', error);
    } finally {
      setLoading(false);
    }
  }, [loading, loadRepoInfo, loadStatus, loadBranches]);

  // Initial load
  useEffect(() => {
    loadAll();
  }, []);

  // Subscribe to backend SCM websocket events (scm.status_changed, scm.branch_changed)
  useEffect(() => {
    const handler = (evt: any) => {
      const eventType = evt?.event || evt?.type || '';
      if (eventType.includes('status_changed')) {
        loadStatus();
      } else if (eventType.includes('branch_changed')) {
        loadRepoInfo();
        loadBranches();
      } else if (eventType.startsWith('scm.')) {
        // Fallback: refresh lightweight pieces
        loadStatus();
      }
    };

    // backendService may expose an EventEmitter API
    try {
      backendService.on?.('scm_event', handler);
    } catch (_) { /* ignore */ }

    return () => {
      try { backendService.off?.('scm_event', handler); } catch (_) { /* ignore */ }
    };
  }, [loadStatus, loadRepoInfo, loadBranches]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) {
        loadStatus();
      }
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

  const handleDiscard = useCallback(async (paths: string[]) => {
    try {
      if (!confirm(`Are you sure you want to discard changes to ${paths.length} file(s)? This cannot be undone.`)) {
        return;
      }
      
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
  
  const handleShowDiff = useCallback((path: string) => {
    console.log('[ICUIGit] handleShowDiff -> open diff in editor for', path);
    if (onOpenDiffPatch) {
      onOpenDiffPatch(path);
      return;
    }
    // Fallback: dispatch global event only (no modal)
    try {
      window.dispatchEvent(new CustomEvent('icui:openDiffPatch', { detail: { path } }));
    } catch (e) {
      console.warn('[ICUIGit] Global diff event dispatch failed:', e);
    }
  }, [onOpenDiffPatch]);

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
    onStage: () => void;
    onUnstage: () => void;
    onDiscard: () => void;
    onShowDiff: () => void;
    onOpen: () => void;
  }> = ({ file, isStaged, onStage, onUnstage, onDiscard, onShowDiff, onOpen }) => {
    const statusConfig = GIT_STATUS_CONFIG[file.status as GitStatusType] || GIT_STATUS_CONFIG['?'];
    
    return (
      <div className="flex items-center justify-between px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 group">
        <div className="flex items-center space-x-2 flex-1 min-w-0">
          <span className={`text-xs font-mono ${statusConfig.color}`}>
            {statusConfig.icon}
          </span>
          <span className="text-sm truncate" title={file.path}>
            {file.path}
          </span>
        </div>
        
        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!isStaged && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onStage}
              title="Stage file"
              className="h-6 w-6 p-0"
            >
              <Plus className="h-3 w-3" />
            </Button>
          )}
          
          {isStaged && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onUnstage}
              title="Unstage file"
              className="h-6 w-6 p-0"
            >
              <Minus className="h-3 w-3" />
            </Button>
          )}
          
          {!isStaged && file.status !== '?' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onDiscard}
              title="Discard changes"
              className="h-6 w-6 p-0"
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
          )}
          
          <Button
            size="sm"
            variant="ghost"
            onClick={onShowDiff}
            title="Show diff"
            className="h-6 w-6 p-0"
          >
            <Eye className="h-3 w-3" />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={onOpen}
            title="Open file"
            className="h-6 w-6 p-0"
          >
            <FileText className="h-3 w-3" />
          </Button>
        </div>
      </div>
    );
  };

  // ==================== Render ====================
  
  if (!isConnected) {
    return (
      <div className={`flex flex-col h-full ${className}`}>
        <div className="flex items-center justify-between p-3 border-b">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowBranchInput(s => !s)}
            title="Create branch"
            className="h-6 px-1 text-xs"
          >+branch</Button>
          <h3 className="text-sm font-medium">Source Control</h3>
          <Button
            size="sm"
            variant="ghost"
            onClick={loadAll}
            title="Refresh"
            className="h-6 w-6 p-0"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center text-gray-500">
            <GitBranch className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No Git repository detected</p>
            <p className="text-xs mt-1">Initialize a repository to use source control</p>
          </div>
        </div>
      </div>
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
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePull}
                title="Pull"
                className="h-6 w-6 p-0"
                disabled={loading}
              >
                <Download className="h-3 w-3" />
              </Button>
              
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handlePush()}
                title="Push"
                className="h-6 w-6 p-0"
                disabled={loading}
              >
                <Upload className="h-3 w-3" />
              </Button>
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
          {repoInfo.remotes.length > 0 && (
            <p className="text-xs text-gray-500 truncate">
              {repoInfo.remotes[0].url}
            </p>
          )}
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
                    onStage={() => handleStage([file.path])}
                    onUnstage={() => handleUnstage([file.path])}
                    onDiscard={() => handleDiscard([file.path])}
                    onShowDiff={() => handleShowDiff(file.path)}
                    onOpen={() => onFileOpen?.(file.path)}
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
                    onStage={() => handleStage([file.path])}
                    onUnstage={() => handleUnstage([file.path])}
                    onDiscard={() => handleDiscard([file.path])}
                    onShowDiff={() => handleShowDiff(file.path)}
                    onOpen={() => onFileOpen?.(file.path)}
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
    </div>
  );
};

export default ICUIGit;
