"""
Test 4: Image Rename Resilience
Tests that the system can still find and load images even after they are renamed.
"""
import os
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')

import pytest
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from icpy.services.image_resolver import ImageResolver, resolve_image_path
from icpy.services.image_reference_service import ImageReference, create_image_reference


class TestImageRenameResilience:
    """Test suite for image resolution after file renames"""
    
    @pytest.fixture
    def workspace_dir(self, tmp_path):
        """Create temporary workspace"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        thumbnails_dir = workspace / ".icotes" / "thumbnails"
        thumbnails_dir.mkdir(parents=True)
        return workspace
    
    @pytest.fixture
    def create_test_image_file(self, workspace_dir):
        """Create a real test image file"""
        from PIL import Image
        import io
        import base64
        
        def _create(filename='test.png'):
            img = Image.new('RGB', (100, 100), color='blue')
            path = workspace_dir / filename
            img.save(path, format='PNG')
            
            # Return base64 for reference creation
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return path, b64
        return _create
    
    @pytest.mark.asyncio
    async def test_resolve_image_by_current_filename(self, workspace_dir, create_test_image_file):
        """Test resolving image using current_filename (no rename)"""
        # Create image
        image_path, base64_data = create_test_image_file('original.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='original.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Resolve should find it at current path
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
        assert Path(resolved_path).name == 'original.png'
    
    @pytest.mark.asyncio
    async def test_resolve_image_after_simple_rename(self, workspace_dir, create_test_image_file):
        """Test resolving image after it's been renamed"""
        # Create image
        image_path, base64_data = create_test_image_file('before.png')
        
        # Create reference with original name
        ref = await create_image_reference(
            image_data=base64_data,
            filename='before.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Rename the file
        new_path = workspace_dir / 'after.png'
        shutil.move(str(image_path), str(new_path))
        
        # Resolve should still find it
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
        assert Path(resolved_path).name == 'after.png'
    
    @pytest.mark.asyncio
    async def test_resolve_image_by_image_id_in_filename(self, workspace_dir, create_test_image_file):
        """Test resolving image by searching for image_id in filenames"""
        # Create image
        image_path, base64_data = create_test_image_file('test.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='test.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Rename file to include image_id
        new_filename = f"renamed_{ref.image_id}.png"
        new_path = workspace_dir / new_filename
        shutil.move(str(image_path), str(new_path))
        
        # Resolve should find it by image_id
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
        assert ref.image_id in Path(resolved_path).name
    
    @pytest.mark.asyncio
    async def test_resolve_image_by_checksum(self, workspace_dir, create_test_image_file):
        """Test resolving image by checksum when filename completely different"""
        # Create image
        image_path, base64_data = create_test_image_file('original.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='original.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Rename to completely different name
        new_path = workspace_dir / 'totally_different_name_xyz.png'
        shutil.move(str(image_path), str(new_path))
        
        # Resolve should find it by checksum
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
    
    @pytest.mark.asyncio
    async def test_resolve_falls_back_to_thumbnail(self, workspace_dir, create_test_image_file):
        """Test that if original image is deleted, thumbnail path is returned"""
        # Create image
        image_path, base64_data = create_test_image_file('will_be_deleted.png')
        
        # Create reference (this creates thumbnail)
        ref = await create_image_reference(
            image_data=base64_data,
            filename='will_be_deleted.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Delete original image
        image_path.unlink()
        
        # Resolve should return thumbnail path
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
        assert 'thumbnails' in resolved_path
    
    @pytest.mark.asyncio
    async def test_resolve_returns_none_if_nothing_found(self, workspace_dir):
        """Test that None is returned if image can't be found anywhere"""
        # Create a reference without creating actual files
        ref = ImageReference(
            image_id="nonexistent-123",
            original_filename="never_existed.png",
            current_filename="never_existed.png",
            relative_path="never_existed.png",
            absolute_path=str(workspace_dir / "never_existed.png"),
            mime_type="image/png",
            size_bytes=1000,
            thumbnail_base64="fake",
            thumbnail_path=str(workspace_dir / ".icotes" / "thumbnails" / "nonexistent-123.webp"),
            prompt="test",
            model="test",
            timestamp=123456.0,
            checksum="fake_checksum"
        )
        
        # Resolve should return None
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is None
    
    @pytest.mark.asyncio
    async def test_resolve_strategy_order(self, workspace_dir, create_test_image_file):
        """Test that resolution tries strategies in correct order"""
        # Create image
        image_path, base64_data = create_test_image_file('test.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='test.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        
        # Strategy order should be:
        # 1. Current filename at relative path
        # 2. Search by image_id in filename
        # 3. Search by checksum
        # 4. Fallback to thumbnail
        
        # Test that current filename is tried first (fastest)
        resolved = await resolver.resolve_image_path(ref)
        assert resolved is not None
        assert Path(resolved).name == 'test.png'
    
    @pytest.mark.asyncio
    async def test_resolver_caches_results(self, workspace_dir, create_test_image_file):
        """Test that resolver caches successful resolutions for performance"""
        # Create image
        image_path, base64_data = create_test_image_file('cached.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='cached.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        
        # First resolution
        resolved1 = await resolver.resolve_image_path(ref)
        
        # Second resolution (should use cache)
        resolved2 = await resolver.resolve_image_path(ref)
        
        assert resolved1 == resolved2
        
        # Check cache was used (should have cached entry)
        assert ref.image_id in resolver._resolution_cache
    
    @pytest.mark.asyncio
    async def test_resolve_updates_current_filename(self, workspace_dir, create_test_image_file):
        """Test that reference is updated with current filename after resolution"""
        # Create image
        image_path, base64_data = create_test_image_file('original.png')
        
        # Create reference
        ref = await create_image_reference(
            image_data=base64_data,
            filename='original.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Rename file
        new_path = workspace_dir / 'renamed.png'
        shutil.move(str(image_path), str(new_path))
        
        # Resolve
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref, update_reference=True)
        
        # Current filename should be updated
        assert ref.current_filename == 'renamed.png'
    
    @pytest.mark.asyncio
    async def test_resolve_with_subdirectories(self, workspace_dir, create_test_image_file):
        """Test resolution works with images in subdirectories"""
        # Create subdirectory
        subdir = workspace_dir / 'images'
        subdir.mkdir()
        
        # Create image in subdirectory
        img_path = subdir / 'test.png'
        from PIL import Image
        import base64, io
        
        img = Image.new('RGB', (100, 100), color='green')
        img.save(img_path)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Create reference with relative path
        ref = await create_image_reference(
            image_data=b64,
            filename='images/test.png',
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Resolve should find it
        resolver = ImageResolver(workspace_path=str(workspace_dir))
        resolved_path = await resolver.resolve_image_path(ref)
        
        assert resolved_path is not None
        assert Path(resolved_path).exists()
        assert 'images' in resolved_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
