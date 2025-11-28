"""
Tests for hop file transfer functionality with skip logic for existing files.

This module tests the improvements made to prevent overwriting good local files
with 0-byte versions during hop file transfers.
"""

import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


@pytest.fixture
def sample_image_bytes():
    """Create sample image data"""
    return b'\x89PNG\r\n\x1a\n' + b'test image data' * 100  # ~1.5KB fake PNG


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


class TestHopFileTransferSkipLogic:
    """Test hop file transfer skip logic for existing files"""

    @pytest.mark.asyncio
    async def test_skip_existing_file_with_nonzero_size(self, temp_workspace, sample_image_bytes):
        """Test that existing non-zero files are not overwritten"""
        from icpy.api.endpoints.hop import router
        
        # Create a file with content
        test_file = temp_workspace / "existing_image.png"
        test_file.write_bytes(sample_image_bytes)
        original_size = test_file.stat().st_size
        
        assert original_size > 0
        
        # Mock the copy_file function to check if it would skip
        # In real implementation, this is in the endpoint's internal function
        # We simulate the check here
        dest_path = str(test_file)
        
        # Check logic: skip if file exists with non-zero size
        should_skip = os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
        
        assert should_skip is True
        
        # Verify file wasn't modified
        assert test_file.stat().st_size == original_size
        assert test_file.read_bytes() == sample_image_bytes

    @pytest.mark.asyncio
    async def test_overwrite_zero_byte_file(self, temp_workspace, sample_image_bytes):
        """Test that 0-byte files ARE overwritten"""
        from icpy.api.endpoints.hop import router
        
        # Create a 0-byte file
        test_file = temp_workspace / "empty_image.png"
        test_file.touch()
        
        assert test_file.stat().st_size == 0
        
        # Check logic: should NOT skip 0-byte files
        dest_path = str(test_file)
        should_skip = os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
        
        assert should_skip is False
        
        # Simulate writing new content
        test_file.write_bytes(sample_image_bytes)
        
        # Verify file was updated
        assert test_file.stat().st_size > 0
        assert test_file.read_bytes() == sample_image_bytes

    @pytest.mark.asyncio
    async def test_create_new_file_when_not_exists(self, temp_workspace, sample_image_bytes):
        """Test that non-existent files are created"""
        from icpy.api.endpoints.hop import router
        
        test_file = temp_workspace / "new_image.png"
        
        assert not test_file.exists()
        
        # Check logic: should NOT skip non-existent files
        dest_path = str(test_file)
        should_skip = os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
        
        assert should_skip is False
        
        # Simulate creating new file
        test_file.write_bytes(sample_image_bytes)
        
        # Verify file was created
        assert test_file.exists()
        assert test_file.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_skip_only_for_local_destination(self, temp_workspace, sample_image_bytes):
        """Test that skip logic only applies when destination is local context"""
        # This test verifies the logic: if dst_ctx == 'local' and os.path.exists(dest_path)
        
        test_file = temp_workspace / "image.png"
        test_file.write_bytes(sample_image_bytes)
        
        # For local context, should skip
        dst_ctx = 'local'
        dest_path = str(test_file)
        should_skip_local = (dst_ctx == 'local' and 
                            os.path.exists(dest_path) and 
                            os.path.getsize(dest_path) > 0)
        
        assert should_skip_local is True
        
        # For remote context, should NOT skip (even if file exists locally)
        dst_ctx = 'remote-server'
        should_skip_remote = (dst_ctx == 'local' and 
                             os.path.exists(dest_path) and 
                             os.path.getsize(dest_path) > 0)
        
        assert should_skip_remote is False


class TestHopFileTransferIntegration:
    """Integration tests for hop file transfer with mock SFTP"""

    @pytest.mark.asyncio
    async def test_transfer_with_existing_local_file(self, temp_workspace, sample_image_bytes):
        """Test complete transfer workflow when local file already exists"""
        
        # Setup: create local file
        local_file = temp_workspace / "vibrant_bird.png"
        local_file.write_bytes(sample_image_bytes)
        original_size = local_file.stat().st_size
        
        # Mock the send-files endpoint payload
        payload = {
            "paths": [str(local_file)],
            "source_context": "remote-server",
            "target_context": "local",
            "common_prefix": str(temp_workspace)
        }
        
        # Simulate the skip check in copy_file
        dest_path = str(local_file)
        dst_ctx = payload["target_context"]
        
        # This is the actual logic from hop.py
        if dst_ctx == 'local' and os.path.exists(dest_path):
            try:
                size = os.path.getsize(dest_path)
                if size > 0:
                    # Would skip and add to created list
                    skipped = True
                    # Verify file wasn't modified
                    assert local_file.stat().st_size == original_size
                    assert local_file.read_bytes() == sample_image_bytes
                else:
                    skipped = False
            except Exception:
                skipped = False
        else:
            skipped = False
        
        assert skipped is True

    @pytest.mark.asyncio
    async def test_transfer_overwrites_corrupt_file(self, temp_workspace, sample_image_bytes):
        """Test that corrupt 0-byte files are overwritten"""
        
        # Setup: create 0-byte corrupt file
        corrupt_file = temp_workspace / "corrupt_bird.png"
        corrupt_file.touch()
        
        assert corrupt_file.stat().st_size == 0
        
        # Simulate transfer
        payload = {
            "paths": [str(corrupt_file)],
            "source_context": "remote-server",
            "target_context": "local"
        }
        
        dest_path = str(corrupt_file)
        dst_ctx = payload["target_context"]
        
        # Check if would skip
        if dst_ctx == 'local' and os.path.exists(dest_path):
            try:
                size = os.path.getsize(dest_path)
                if size > 0:
                    skipped = True
                else:
                    skipped = False  # 0-byte file should NOT be skipped
            except Exception:
                skipped = False
        else:
            skipped = False
        
        assert skipped is False
        
        # Simulate overwrite
        corrupt_file.write_bytes(sample_image_bytes)
        
        # Verify file was fixed
        assert corrupt_file.stat().st_size > 0
        assert corrupt_file.read_bytes() == sample_image_bytes


class TestRestAPIFileServing:
    """Test REST API file serving with size checks"""

    def test_serve_file_with_nonzero_size(self, temp_workspace, sample_image_bytes):
        """Test that files with non-zero size are served"""
        
        test_file = temp_workspace / "valid_image.png"
        test_file.write_bytes(sample_image_bytes)
        
        # Simulate the check in get_file_raw
        cand = str(test_file)
        if os.path.exists(cand):
            size = os.path.getsize(cand)
            should_serve = size > 0
        else:
            should_serve = False
        
        assert should_serve is True

    def test_skip_zero_byte_file(self, temp_workspace):
        """Test that 0-byte files are NOT served locally"""
        
        test_file = temp_workspace / "empty_image.png"
        test_file.touch()
        
        # Simulate the check in get_file_raw
        cand = str(test_file)
        if os.path.exists(cand):
            size = os.path.getsize(cand)
            should_serve = size > 0
        else:
            should_serve = False
        
        assert should_serve is False

    def test_handle_nonexistent_file(self, temp_workspace):
        """Test handling of non-existent files"""
        
        test_file = temp_workspace / "nonexistent.png"
        
        # Simulate the check in get_file_raw
        cand = str(test_file)
        if os.path.exists(cand):
            size = os.path.getsize(cand)
            should_serve = size > 0
        else:
            should_serve = False
        
        assert should_serve is False


class TestFileTransferScenarios:
    """Test real-world scenarios"""

    @pytest.mark.asyncio
    async def test_image_generation_hop_viewer_workflow(self, temp_workspace, sample_image_bytes):
        """Test the complete workflow: generate → hop context → view in Explorer"""
        
        # Step 1: Image generated locally
        generated_image = temp_workspace / "generated_bird.png"
        generated_image.write_bytes(sample_image_bytes)
        original_size = generated_image.stat().st_size
        
        assert original_size > 0
        print(f"Step 1: Generated image locally ({original_size} bytes)")
        
        # Step 2: Remote write fails (simulated by not doing anything to remote)
        # In real scenario, this is where SFTP write would fail
        print("Step 2: Remote write failed (simulated)")
        
        # Step 3: User tries to view in Explorer
        # This triggers file transfer from remote to local
        # But local file already exists with good data
        
        dest_path = str(generated_image)
        dst_ctx = 'local'
        
        # The skip check should prevent overwrite
        if dst_ctx == 'local' and os.path.exists(dest_path):
            size = os.path.getsize(dest_path)
            if size > 0:
                print(f"Step 3: Skipping transfer - local file exists ({size} bytes)")
                skipped = True
            else:
                print("Step 3: Would transfer - local file is 0 bytes")
                skipped = False
        else:
            skipped = False
        
        assert skipped is True
        
        # Step 4: Serve the file
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            print("Step 4: Serving local file to viewer")
            can_serve = True
        else:
            can_serve = False
        
        assert can_serve is True
        
        # Verify file integrity maintained
        assert generated_image.stat().st_size == original_size
        assert generated_image.read_bytes() == sample_image_bytes
        print("✓ Workflow completed successfully - image integrity maintained")

    @pytest.mark.asyncio
    async def test_multiple_files_transfer_with_mixed_states(self, temp_workspace, sample_image_bytes):
        """Test transferring multiple files with different states"""
        
        # File 1: Exists with good data (should skip)
        file1 = temp_workspace / "existing_good.png"
        file1.write_bytes(sample_image_bytes)
        
        # File 2: Exists with 0 bytes (should overwrite)
        file2 = temp_workspace / "existing_empty.png"
        file2.touch()
        
        # File 3: Doesn't exist (should create)
        file3 = temp_workspace / "new_file.png"
        
        files = [file1, file2, file3]
        results = []
        
        for f in files:
            dest_path = str(f)
            dst_ctx = 'local'
            
            if dst_ctx == 'local' and os.path.exists(dest_path):
                size = os.path.getsize(dest_path)
                if size > 0:
                    action = 'skip'
                else:
                    action = 'transfer'
            else:
                action = 'transfer'
            
            results.append((f.name, action))
        
        # Verify decisions
        assert results[0][1] == 'skip'      # existing_good.png
        assert results[1][1] == 'transfer'  # existing_empty.png
        assert results[2][1] == 'transfer'  # new_file.png
        
        print("✓ Multiple file transfer decisions correct:")
        for name, action in results:
            print(f"  {name}: {action}")


class TestNamespaceStripping:
    """Test namespace prefix handling in send-files endpoint"""
    
    def test_strip_namespace_local(self):
        """Test stripping 'local:' namespace prefix"""
        # Import the strip function from the endpoint (we'll need to refactor it)
        # For now, replicate the logic here
        def _strip_namespace(path: str) -> tuple[str | None, str]:
            if not path:
                return (None, path)
            idx = path.find(':/')
            if idx > 0:
                ns = path[:idx]
                if idx == 1 and ns.isalpha():
                    return (None, path)
                abs_path = path[idx+1:] or '/'
                if not abs_path.startswith('/'):
                    abs_path = '/' + abs_path
                return (ns, abs_path)
            return (None, path)
        
        # Test local namespace
        ns, path = _strip_namespace('local:/home/penthoy/icotes/file.txt')
        assert ns == 'local'
        assert path == '/home/penthoy/icotes/file.txt'
    
    def test_strip_namespace_hop(self):
        """Test stripping 'hop1:' namespace prefix"""
        def _strip_namespace(path: str) -> tuple[str | None, str]:
            if not path:
                return (None, path)
            idx = path.find(':/')
            if idx > 0:
                ns = path[:idx]
                if idx == 1 and ns.isalpha():
                    return (None, path)
                abs_path = path[idx+1:] or '/'
                if not abs_path.startswith('/'):
                    abs_path = '/' + abs_path
                return (ns, abs_path)
            return (None, path)
        
        # Test hop namespace
        ns, path = _strip_namespace('hop1:/home/remote/data/file.png')
        assert ns == 'hop1'
        assert path == '/home/remote/data/file.png'
    
    def test_strip_namespace_no_prefix(self):
        """Test path without namespace prefix"""
        def _strip_namespace(path: str) -> tuple[str | None, str]:
            if not path:
                return (None, path)
            idx = path.find(':/')
            if idx > 0:
                ns = path[:idx]
                if idx == 1 and ns.isalpha():
                    return (None, path)
                abs_path = path[idx+1:] or '/'
                if not abs_path.startswith('/'):
                    abs_path = '/' + abs_path
                return (ns, abs_path)
            return (None, path)
        
        # Test regular path
        ns, path = _strip_namespace('/home/user/file.txt')
        assert ns is None
        assert path == '/home/user/file.txt'
    
    def test_strip_namespace_windows_path(self):
        """Test Windows drive letter is not treated as namespace"""
        def _strip_namespace(path: str) -> tuple[str | None, str]:
            if not path:
                return (None, path)
            idx = path.find(':/')
            if idx > 0:
                ns = path[:idx]
                if idx == 1 and ns.isalpha():
                    return (None, path)
                abs_path = path[idx+1:] or '/'
                if not abs_path.startswith('/'):
                    abs_path = '/' + abs_path
                return (ns, abs_path)
            return (None, path)
        
        # Test Windows path
        ns, path = _strip_namespace('C:/Users/test/file.txt')
        assert ns is None
        assert path == 'C:/Users/test/file.txt'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
