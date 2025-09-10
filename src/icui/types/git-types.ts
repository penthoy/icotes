/**
 * Git/SCM Type Definitions for ICUI Git Panel
 * 
 * Defines TypeScript interfaces for Git operations and data structures
 * used by the ICUIGit panel and backend service integration.
 */

export interface GitFileChange {
  path: string;
  status: 'M' | 'A' | 'D' | 'R' | 'U' | '?';
}

export interface GitStatus {
  staged: GitFileChange[];
  unstaged: GitFileChange[];
  untracked: GitFileChange[];
}

export interface GitRemote {
  name: string;
  url: string;
}

export interface GitRepoInfo {
  root: string;
  branch: string;
  remotes: GitRemote[];
  ahead: number;
  behind: number;
  clean: boolean;
}

export interface GitDiff {
  path: string | null;
  patch: string;
}

export interface GitBranches {
  current: string;
  local: string[];
}

export interface GitCommitOptions {
  message: string;
  amend?: boolean;
  signoff?: boolean;
}

export interface GitCheckoutOptions {
  branch: string;
  create?: boolean;
}

export interface GitPushOptions {
  set_upstream?: boolean;
}

export interface GitApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

// Git status badge colors and icons
export const GIT_STATUS_CONFIG = {
  'M': { label: 'Modified', color: 'text-yellow-500', icon: '●' },
  'A': { label: 'Added', color: 'text-green-500', icon: '+' },
  'D': { label: 'Deleted', color: 'text-red-500', icon: '−' },
  'R': { label: 'Renamed', color: 'text-blue-500', icon: '→' },
  'U': { label: 'Unmerged', color: 'text-purple-500', icon: '⚠' },
  '?': { label: 'Untracked', color: 'text-gray-500', icon: '?' },
} as const;

export type GitStatusType = keyof typeof GIT_STATUS_CONFIG;
