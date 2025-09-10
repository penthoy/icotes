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
}

const ICUIGit: React.FC<ICUIGitProps> = ({
  className = '',
  onFileSelect,
  onFileOpen,
}) => {
  // State management
  const [repoInfo, setRepoInfo] = useState<GitRepoInfo | null>(null);
  const [status, setStatus] = useState<GitStatus>({ staged: [], unstaged: [], untracked: [] });
  const [branches, setBranches] = useState<GitBranches>({ current: '', local: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
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
  const [diffPreview, setDiffPreview] = useState<{ path: string; patch: string } | null>(null);
  
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
    if (!commitMessage.trim()) {
      setError('Commit message is required');
      return;
    }
    
    try {
      setLoading(true);
      const success = await backendService.scmCommit(
        commitMessage.trim(),
        commitOptions.amend,
        commitOptions.signoff
      );
      
      if (success) {
        setCommitMessage('');
        setCommitOptions({ amend: false, signoff: false });
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
  }, [commitMessage, commitOptions, loadAll]);

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

  // ==================== Diff Preview ====================
  
  const handleShowDiff = useCallback(async (path: string) => {
    try {
      const diff = await backendService.getScmDiff(path);
      setDiffPreview(diff);
    } catch (error) {
      console.error('[ICUIGit] Failed to get diff:', error);
      setError(error instanceof Error ? error.message : 'Failed to get diff');
    }
  }, []);

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

  const canCommit = useMemo(() => 
    status.staged.length > 0 && commitMessage.trim().length > 0,
    [status.staged.length, commitMessage]
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
          
          {repoInfo.remotes.length > 0 && (
            <p className="text-xs text-gray-500 truncate">
              {repoInfo.remotes[0].url}
            </p>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Changes Section */}
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
            
            {allUnstagedFiles.length > 0 && (
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
            )}
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
              
              {allUnstagedFiles.length === 0 && (
                <div className="p-4 text-center text-gray-500 text-sm">
                  No changes
                </div>
              )}
            </div>
          )}
        </div>

        {/* Staged Changes Section */}
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
            
            {status.staged.length > 0 && (
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
            )}
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
              
              {status.staged.length === 0 && (
                <div className="p-4 text-center text-gray-500 text-sm">
                  No staged changes
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Commit Section */}
      <div className="p-3 border-t bg-gray-50 dark:bg-gray-800">
        <textarea
          ref={commitTextareaRef}
          value={commitMessage}
          onChange={(e) => setCommitMessage(e.target.value)}
          placeholder="Commit message"
          rows={3}
          className="w-full p-2 text-sm border rounded resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
        />
        
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
            className="flex items-center space-x-1"
          >
            <GitCommit className="h-3 w-3" />
            <span>Commit</span>
          </Button>
        </div>
      </div>

      {/* Diff Preview Modal */}
      {diffPreview && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg w-11/12 h-5/6 flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-medium">Diff: {diffPreview.path}</h3>
              <Button
                variant="ghost"
                onClick={() => setDiffPreview(null)}
                className="h-8 w-8 p-0"
              >
                ✕
              </Button>
            </div>
            
            <div className="flex-1 overflow-auto p-4">
              <pre className="text-xs font-mono whitespace-pre-wrap">
                {diffPreview.patch}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ICUIGit;
