"""
Tests for Source Control Service

Basic integration tests for the generic SCM service with Git provider.
Uses a temporary git repository fixture for isolated testing.
"""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path

from icpy.services.source_control_service import (
    SourceControlService,
    GitSourceControlProvider,
    RepoInfo
)


@pytest.fixture
async def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        
        # Initialize git repo
        proc = await asyncio.create_subprocess_exec(
            "git", "init", str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        # Configure git (required for commits)
        await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "config", "user.name", "Test User"
        )
        await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "config", "user.email", "test@example.com"
        )
        
        # Create initial file and commit
        test_file = repo_path / "test.txt"
        test_file.write_text("initial content\n")
        
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "add", "test.txt"
        )
        await proc.communicate()
        
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "commit", "-m", "Initial commit"
        )
        await proc.communicate()
        
        # Wait a bit to ensure git operations complete
        await asyncio.sleep(0.1)
        
        yield str(repo_path)


@pytest.mark.asyncio
async def test_git_provider_basic_operations(temp_git_repo):
    """Test basic Git provider operations."""
    provider = GitSourceControlProvider(temp_git_repo)
    
    # Test repo info
    info = await provider.get_repo_info()
    assert isinstance(info, RepoInfo)
    assert info.root == temp_git_repo
    assert info.branch  # Should have a branch (main/master)
    # Note: clean status depends on git state - just check it's a boolean
    assert isinstance(info.clean, bool)
    
    # Test status
    status = await provider.status()
    assert "staged" in status
    assert "unstaged" in status
    assert "untracked" in status
    assert isinstance(status["staged"], list)
    assert isinstance(status["unstaged"], list) 
    assert isinstance(status["untracked"], list)
    
    # Test branches
    branches = await provider.branches()
    assert "current" in branches
    assert "local" in branches
    assert branches["current"]  # Should have a current branch


@pytest.mark.asyncio
async def test_git_provider_file_operations(temp_git_repo):
    """Test Git provider file operations (stage, unstage, commit)."""
    provider = GitSourceControlProvider(temp_git_repo)
    
    # Create a new file
    new_file = Path(temp_git_repo) / "new_file.txt"
    new_file.write_text("new content\n")
    
    # Check status - should show untracked
    status = await provider.status()
    untracked_files = [f["path"] for f in status["untracked"]]
    assert "new_file.txt" in untracked_files
    
    # Stage the file
    success = await provider.stage(["new_file.txt"])
    assert success
    
    # Check status - should show staged
    status = await provider.status()
    staged_files = [f["path"] for f in status["staged"]]
    assert "new_file.txt" in staged_files
    
    # Unstage the file
    success = await provider.unstage(["new_file.txt"])
    assert success
    
    # Check status - should be back to untracked
    status = await provider.status()
    staged_files = [f["path"] for f in status["staged"]]
    untracked_files = [f["path"] for f in status["untracked"]]
    assert "new_file.txt" not in staged_files
    assert "new_file.txt" in untracked_files
    
    # Stage and commit
    await provider.stage(["new_file.txt"])
    success = await provider.commit("Add new file")
    assert success
    
    # Check status - new_file should no longer be untracked
    status = await provider.status()
    untracked_files = [f["path"] for f in status["untracked"]]
    assert "new_file.txt" not in untracked_files


@pytest.mark.asyncio
async def test_source_control_service(temp_git_repo):
    """Test the SourceControlService wrapper."""
    service = SourceControlService(temp_git_repo)
    await service.initialize()
    
    # Test repo info through service
    info = await service.get_repo_info()
    assert "root" in info
    assert "branch" in info
    assert "clean" in info
    assert info["root"] == temp_git_repo
    
    # Test status through service
    status = await service.status()
    assert "staged" in status
    assert "unstaged" in status
    assert "untracked" in status


@pytest.mark.asyncio
async def test_path_safety(temp_git_repo):
    """Test that path operations are restricted to workspace root."""
    provider = GitSourceControlProvider(temp_git_repo)
    
    # Test with path outside workspace
    with pytest.raises(ValueError, match="Path outside workspace"):
        provider._safe_paths(["../outside.txt"])
    
    # Test with absolute path outside workspace
    with pytest.raises(ValueError, match="Path outside workspace"):
        provider._safe_paths(["/tmp/outside.txt"])
    
    # Test with valid relative path
    safe_paths = provider._safe_paths(["valid.txt"])
    assert safe_paths == ["valid.txt"]
    
    # Test with valid absolute path within workspace
    valid_abs = os.path.join(temp_git_repo, "valid.txt")
    safe_paths = provider._safe_paths([valid_abs])
    assert safe_paths == ["valid.txt"]


if __name__ == "__main__":
    pytest.main([__file__])
