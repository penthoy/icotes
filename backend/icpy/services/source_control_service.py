"""
Generic Source Control Service (SCM) with pluggable providers.

This module defines a provider interface for source control systems and a
service that selects and delegates to a concrete provider. The initial
implementation includes a Git provider using the system `git` binary via
async subprocess calls. The design is intentionally generic to allow adding
other providers later (e.g., GitHub API workflows, SVN, etc.).

Conventions:
- Never operate outside the configured workspace root.
- Sanitize user inputs (paths, branch names) to avoid traversal or injection.
- Publish events on state changes via the message broker with `scm.*` topics.

Author: GitHub Copilot
Date: 2025-09-08
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..core.message_broker import get_message_broker
from .filesystem_service import get_filesystem_service

logger = logging.getLogger(__name__)


# ----------------------------- Types / Contracts -----------------------------

@dataclass
class RepoInfo:
    root: str
    branch: str
    remotes: List[Dict[str, str]]
    ahead: int
    behind: int
    clean: bool


class SourceControlProvider:
    """Abstract base for source control providers."""

    def __init__(self, workspace_root: str, timeout: float = 10.0):
        self.workspace_root = os.path.abspath(workspace_root)
        self.timeout = timeout

    # Query ops
    async def get_repo_info(self) -> Optional[RepoInfo]:
        raise NotImplementedError

    async def status(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def diff(self, path: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    async def branches(self) -> Dict[str, Any]:
        raise NotImplementedError

    # Mutations
    async def stage(self, paths: List[str]) -> bool:
        raise NotImplementedError

    async def unstage(self, paths: List[str]) -> bool:
        raise NotImplementedError

    async def discard(self, paths: List[str]) -> bool:
        raise NotImplementedError

    async def commit(self, message: str, amend: bool = False, signoff: bool = False) -> bool:
        raise NotImplementedError

    async def checkout(self, branch: str, create: bool = False) -> bool:
        raise NotImplementedError

    async def pull(self) -> bool:
        raise NotImplementedError

    async def push(self, set_upstream: bool = False) -> bool:
        raise NotImplementedError


# --------------------------------- Git Provider ---------------------------------

class GitSourceControlProvider(SourceControlProvider):
    """Git provider using the system `git` binary.

    Notes:
    - Uses `git -C <root>` to force all commands under the workspace root.
    - Parses `status --porcelain=v2 --branch` for stable output.
    """

    def _safe_paths(self, paths: List[str]) -> List[str]:
        safe: List[str] = []
        for p in paths:
            if not p:
                continue
            # Normalize and ensure within workspace_root
            abspath = (
                os.path.abspath(os.path.join(self.workspace_root, p))
                if not os.path.isabs(p) else os.path.abspath(p)
            )
            try:
                # Use realpath to resolve symlinks and commonpath for safer containment check
                workspace_real = os.path.realpath(self.workspace_root)
                abspath_real = os.path.realpath(abspath)
                common = os.path.commonpath([abspath_real, workspace_real])
            except (ValueError, OSError):
                raise ValueError(f"Path outside workspace: {p}")
            if common != workspace_real:
                raise ValueError(f"Path outside workspace: {p}")
            safe.append(os.path.relpath(abspath, self.workspace_root))
        return safe

    async def _run_git(self, *args: str) -> Tuple[int, str, str]:
        cmd = ["git", "-C", self.workspace_root, *args]
        logger.debug(f"[SCM][git] exec: {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError as e:
                try:
                    proc.kill()
                finally:
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                raise TimeoutError(f"git command timed out: {' '.join(args)}") from e
            return proc.returncode, stdout_b.decode("utf-8", errors="replace"), stderr_b.decode("utf-8", errors="replace")
        except FileNotFoundError as e:
            raise RuntimeError("git not found on PATH") from e

    async def _repo_root(self) -> Optional[str]:
        code, out, _ = await self._run_git("rev-parse", "--show-toplevel")
        if code == 0:
            return out.strip()
        return None

    async def get_repo_info(self) -> RepoInfo:
        # Detect repository presence using git (handles nested or parent repos)
        repo_root = await self._repo_root()
        if not repo_root:
            return None  # Not inside a Git repository
        # Branch
        code, branch, _ = await self._run_git("branch", "--show-current")
        current_branch = branch.strip() if code == 0 else ""

        # Remotes
        remotes: List[Dict[str, str]] = []
        code, out, _ = await self._run_git("remote", "-v")
        if code == 0:
            seen = set()
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    name, url = parts[0], parts[1]
                    key = (name, url)
                    if key in seen:
                        continue
                    seen.add(key)
                    remotes.append({"name": name, "url": url})

        # Ahead/Behind
        ahead = behind = 0
        code, out, _ = await self._run_git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        if code != 0:
            code2, out2, _ = await self._run_git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
            if code2 == 0:
                left, right = out2.strip().split()
                ahead, behind = int(right), int(left)
        else:
            left, right = out.strip().split()
            behind, ahead = int(left), int(right)

        status = await self.status()
        clean = not (status.get("staged") or status.get("unstaged") or status.get("untracked"))

        root = repo_root or self.workspace_root
        return RepoInfo(root=root, branch=current_branch, remotes=remotes, ahead=ahead, behind=behind, clean=clean)

    async def status(self) -> Dict[str, Any]:
        code, out, _ = await self._run_git("status", "--porcelain=v2", "--branch")
        if code != 0:
            return {"staged": [], "unstaged": [], "untracked": []}

        staged: List[Dict[str, str]] = []
        unstaged: List[Dict[str, str]] = []
        untracked: List[Dict[str, str]] = []

        for line in out.splitlines():
            if not line or line.startswith("#"):
                continue
            if line.startswith("1 "):
                parts = line.split()
                if len(parts) >= 9:
                    xy = parts[1]
                    path = parts[8]
                    x, y = xy[0], xy[1]
                    entry = {"path": path, "status": (x if x != "." else y)}
                    if x != ".":
                        staged.append(entry)
                    if y != ".":
                        unstaged.append({"path": path, "status": y})
            elif line.startswith("? "):
                path = line[2:].strip()
                untracked.append({"path": path, "status": "?"})

        return {"staged": staged, "unstaged": unstaged, "untracked": untracked}

    async def diff(self, path: Optional[str] = None) -> Dict[str, Any]:
        args = ["diff"]
        if path:
            safe = self._safe_paths([path])[0]
            args.append("--")
            args.append(safe)
        code, out, _ = await self._run_git(*args)
        return {"path": path, "patch": out}

    async def stage(self, paths: List[str]) -> bool:
        if not paths:
            return True
        safe = self._safe_paths(paths)
        code, _, err = await self._run_git("add", "--", *safe)
        if code != 0:
            logger.error(f"git add failed: {err}")
            return False
        return True

    async def unstage(self, paths: List[str]) -> bool:
        if not paths:
            return True
        safe = self._safe_paths(paths)
        # Reset index for given paths
        code, _, err = await self._run_git("reset", "--", *safe)
        if code != 0:
            logger.error(f"git reset failed: {err}")
            return False
        return True

    async def discard(self, paths: List[str]) -> bool:
        if not paths:
            return True
        safe = self._safe_paths(paths)
        # Restore from HEAD for files; untracked removal not done here for safety
        code, _, err = await self._run_git("restore", "--source=HEAD", "--worktree", "--staged", "--", *safe)
        if code != 0:
            logger.error(f"git restore failed: {err}")
            return False
        return True

    async def commit(self, message: str, amend: bool = False, signoff: bool = False) -> bool:
        args = ["commit", "-m", message]
        if amend:
            args.append("--amend")
            args.append("--no-edit")
        if signoff:
            args.append("--signoff")
        code, _, err = await self._run_git(*args)
        if code != 0:
            logger.error(f"git commit failed: {err}")
            return False
        return True

    async def branches(self) -> Dict[str, Any]:
        code, out, _ = await self._run_git("branch", "--list")
        branches: List[str] = []
        current = ""
        if code == 0:
            for line in out.splitlines():
                if line.startswith("*"):
                    current = line[2:].strip()
                    branches.append(current)
                else:
                    branches.append(line.strip())
        return {"current": current, "local": branches, "remote": []}

    async def checkout(self, branch: str, create: bool = False) -> bool:
        # Validate branch name using git's refname rules
        code, _, _ = await self._run_git("check-ref-format", "--branch", branch)
        if code != 0:
            raise ValueError("Invalid branch name")
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)
        code, _, err = await self._run_git(*args)
        if code != 0:
            logger.error(f"git checkout failed: {err}")
            return False
        return True

    async def pull(self) -> bool:
        code, _, err = await self._run_git("pull", "--ff-only")
        if code != 0:
            logger.error(f"git pull failed: {err}")
            return False
        return True

    async def push(self, set_upstream: bool = False) -> bool:
        args = ["push"]
        if set_upstream:
            # Attempt to push and set upstream for current branch
            # Obtain current branch
            _, branch, _ = await self._run_git("branch", "--show-current")
            b = branch.strip()
            if b:
                args = ["push", "-u", "origin", b]
        code, _, err = await self._run_git(*args)
        if code != 0:
            logger.error(f"git push failed: {err}")
            return False
        return True


# ------------------------------- Service Wrapper ------------------------------

class SourceControlService:
    """Service that manages SCM providers and exposes a unified API."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self._provider: Optional[SourceControlProvider] = None
        self._message_broker = None
        self.logger = logger  # Use the module-level logger

    async def initialize(self):
        self._message_broker = await get_message_broker()
        # Auto-detect provider (for now: Git if .git exists)
        provider_name = os.environ.get("SCM_PROVIDER", "auto").lower()
        if provider_name in ("auto", "git"):
            if os.path.isdir(os.path.join(self.workspace_root, ".git")) or provider_name == "git":
                self._provider = GitSourceControlProvider(self.workspace_root)
        if not self._provider:
            # Fallback to Git attempts even without .git; commands will fail gracefully
            self._provider = GitSourceControlProvider(self.workspace_root)

    def _ensure_provider(self) -> SourceControlProvider:
        if not self._provider:
            raise RuntimeError("SourceControlService not initialized")
        return self._provider

    # Delegating API
    async def get_repo_info(self) -> Optional[Dict[str, Any]]:
        info = await self._ensure_provider().get_repo_info()
        if info is None:
            return None
        return {
            "root": info.root,
            "branch": info.branch,
            "remotes": info.remotes,
            "ahead": info.ahead,
            "behind": info.behind,
            "clean": info.clean,
        }

    async def status(self) -> Dict[str, Any]:
        return await self._ensure_provider().status()

    async def diff(self, path: Optional[str] = None) -> Dict[str, Any]:
        return await self._ensure_provider().diff(path)

    async def stage(self, paths: List[str]) -> bool:
        ok = await self._ensure_provider().stage(paths)
        if ok:
            await self._publish("scm.status_changed", {"reason": "stage", "paths": paths})
        return ok

    async def unstage(self, paths: List[str]) -> bool:
        ok = await self._ensure_provider().unstage(paths)
        if ok:
            await self._publish("scm.status_changed", {"reason": "unstage", "paths": paths})
        return ok

    async def discard(self, paths: List[str]) -> bool:
        ok = await self._ensure_provider().discard(paths)
        if ok:
            await self._publish("scm.status_changed", {"reason": "discard", "paths": paths})
        return ok

    async def commit(self, message: str, amend: bool = False, signoff: bool = False) -> bool:
        ok = await self._ensure_provider().commit(message, amend=amend, signoff=signoff)
        if ok:
            await self._publish("scm.status_changed", {"reason": "commit"})
        return ok

    async def branches(self) -> Dict[str, Any]:
        return await self._ensure_provider().branches()

    async def checkout(self, branch: str, create: bool = False) -> bool:
        ok = await self._ensure_provider().checkout(branch, create=create)
        if ok:
            await self._publish("scm.branch_changed", {"branch": branch, "create": create})
        return ok

    async def pull(self) -> bool:
        ok = await self._ensure_provider().pull()
        if ok:
            await self._publish("scm.status_changed", {"reason": "pull"})
        return ok

    async def push(self, set_upstream: bool = False) -> bool:
        ok = await self._ensure_provider().push(set_upstream=set_upstream)
        if ok:
            await self._publish("scm.status_changed", {"reason": "push", "set_upstream": set_upstream})
        return ok

    async def init_repo(self) -> bool:
        """Initialize a Git repository in the workspace."""
        try:
            # Check if a .git directory already exists
            git_dir = os.path.join(self.workspace_root, ".git")
            if os.path.exists(git_dir):
                logger.info(f"[SCM] Git repository already exists at {git_dir}")
                return True
            
            # Run git init in the workspace root
            provider = self._ensure_provider()
            if hasattr(provider, '_run_git'):
                code, _, err = await provider._run_git("init")
                if code == 0:
                    logger.info(f"[SCM] Git repository initialized at {self.workspace_root}")
                    await self._publish("scm.repo_initialized", {"root": self.workspace_root})
                    return True
                else:
                    logger.error(f"[SCM] Git init failed: {err}")
                    return False
            else:
                logger.error("[SCM] Provider does not support git init operation")
                return False
        except Exception as e:
            logger.error(f"[SCM] Failed to initialize Git repository: {e}")
            return False

    async def _publish(self, topic: str, payload: Dict[str, Any]):
        try:
            if not self._message_broker:
                self._message_broker = await get_message_broker()
            await self._message_broker.publish(topic, payload)
        except Exception as e:
            logger.error(f"[SCM] Failed to publish {topic}: {e}")


# ------------------------------ Service Singleton -----------------------------

_source_control_service: Optional[SourceControlService] = None


async def get_source_control_service() -> SourceControlService:
    global _source_control_service
    if _source_control_service is None:
        fs = await get_filesystem_service()
        
        # Try to find the Git repository root by walking up from the filesystem root
        git_root = fs.root_path
        while git_root and git_root != "/":
            if os.path.exists(os.path.join(git_root, ".git")):
                break
            parent = os.path.dirname(git_root)
            if parent == git_root:  # Reached filesystem root
                break
            git_root = parent
        
        # If no .git found, use the filesystem root as fallback
        if not os.path.exists(os.path.join(git_root, ".git")):
            git_root = fs.root_path
            
        logger.info(f"[SCM] Using Git root: {git_root} (filesystem root: {fs.root_path})")
        
        svc = SourceControlService(workspace_root=git_root)
        await svc.initialize()
        _source_control_service = svc
    return _source_control_service


async def shutdown_source_control_service():
    global _source_control_service
    _source_control_service = None
