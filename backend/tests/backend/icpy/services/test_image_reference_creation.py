"""
Test 1: Image Reference Creation
Tests that ImageReference objects are created correctly with all required fields.
"""
import pytest
import os
import base64
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import uuid

# Set dummy API key to avoid import errors
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')

from icpy.services.image_reference_service import (
    ImageReference,
    ImageReferenceService,
    create_image_reference
)


class TestImageReferenceCreation:
    """Test suite for ImageReference creation"""
    
    @pytest.fixture
    def workspace_dir(self, tmp_path):
        """Create a temporary workspace directory"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        thumbnails_dir = workspace / ".icotes" / "thumbnails"
        thumbnails_dir.mkdir(parents=True)
        return workspace
    
    @pytest.fixture
    def sample_image_base64(self):
        """Create a small valid PNG image in base64"""
        # 1x1 red pixel PNG
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='
        )
        return base64.b64encode(png_data).decode('utf-8')
    
    @pytest.fixture
    def sample_image_data_uri(self, sample_image_base64):
        """Create a data URI for the sample image"""
        return f"data:image/png;base64,{sample_image_base64}"
    
    def test_image_reference_dataclass_fields(self):
        """Test that ImageReference has all required fields"""
        ref = ImageReference(
            image_id="test-123",
            original_filename="test.png",
            current_filename="test.png",
            relative_path="test.png",
            absolute_path="/workspace/test.png",
            mime_type="image/png",
            size_bytes=1024,
            thumbnail_base64="thumb_data",
            thumbnail_path="/workspace/.icotes/thumbnails/test-123.webp",
            prompt="test prompt",
            model="test-model",
            timestamp=1234567890.0,
            checksum="abc123",
            session_ids=["session-1"],
            file_type="preview",
            preview_paths=["/workspace/.icotes/thumbnails/test-123.webp"]
        )
        
        assert ref.image_id == "test-123"
        assert ref.original_filename == "test.png"
        assert ref.current_filename == "test.png"
        assert ref.relative_path == "test.png"
        assert ref.absolute_path == "/workspace/test.png"
        assert ref.mime_type == "image/png"
        assert ref.size_bytes == 1024
        assert ref.thumbnail_base64 == "thumb_data"
        assert ref.thumbnail_path == "/workspace/.icotes/thumbnails/test-123.webp"
        assert ref.prompt == "test prompt"
        assert ref.model == "test-model"
        assert ref.timestamp == 1234567890.0
        assert ref.checksum == "abc123"
        assert ref.session_ids == ["session-1"]
        assert ref.file_type == "preview"
    
    def test_image_reference_to_dict(self):
        """Test ImageReference serialization to dict"""
        ref = ImageReference(
            image_id="test-123",
            original_filename="test.png",
            current_filename="test.png",
            relative_path="test.png",
            absolute_path="/workspace/test.png",
            mime_type="image/png",
            size_bytes=1024,
            thumbnail_base64="thumb_data",
            thumbnail_path="/workspace/.icotes/thumbnails/test-123.webp",
            prompt="test prompt",
            model="test-model",
            timestamp=1234567890.0,
            checksum="abc123",
            session_ids=["session-1"],
            file_type="preview"
        )
        
        ref_dict = ref.to_dict()
        
        assert isinstance(ref_dict, dict)
        assert ref_dict['image_id'] == "test-123"
        assert ref_dict['original_filename'] == "test.png"
        assert 'thumbnail_base64' in ref_dict
    
    def test_image_reference_from_dict(self):
        """Test ImageReference deserialization from dict"""
        data = {
            'image_id': "test-123",
            'original_filename': "test.png",
            'current_filename': "test.png",
            'relative_path': "test.png",
            'absolute_path': "/workspace/test.png",
            'mime_type': "image/png",
            'size_bytes': 1024,
            'thumbnail_base64': "thumb_data",
            'thumbnail_path': "/workspace/.icotes/thumbnails/test-123.webp",
            'prompt': "test prompt",
            'model': "test-model",
            'timestamp': 1234567890.0,
            'checksum': "abc123",
            'session_ids': ["session-1"],
            'file_type': "preview"
        }
        
        ref = ImageReference.from_dict(data)
        
        assert ref.image_id == "test-123"
        assert ref.original_filename == "test.png"
        assert ref.prompt == "test prompt"
        assert ref.session_ids == ["session-1"]
        assert ref.file_type == "preview"
    
    @pytest.mark.asyncio
    async def test_create_image_reference_from_base64(self, workspace_dir, sample_image_base64):
        """Test creating ImageReference from base64 image data"""
        # Save a test image to workspace
        filename = "test_generated.png"
        image_path = workspace_dir / filename
        image_bytes = base64.b64decode(sample_image_base64)
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        # Create reference
        ref = await create_image_reference(
            image_data=sample_image_base64,
            filename=filename,
            workspace_path=str(workspace_dir),
            prompt="a test image",
            model="test-model-1"
        )
        
        # Verify all fields populated
        assert ref.image_id is not None
        assert len(ref.image_id) > 0
        assert ref.original_filename == filename
        assert ref.current_filename == filename
        assert ref.relative_path == filename
        assert ref.absolute_path == str(image_path)
        assert ref.mime_type == "image/png"
        assert ref.size_bytes > 0
        assert ref.thumbnail_base64 is not None
        assert len(ref.thumbnail_base64) > 0
        # thumbnail_path is legacy and may be empty (we now generate in-memory base64 thumbnails)
        assert ref.thumbnail_path == '' or ref.thumbnail_path is None
        assert ref.prompt == "a test image"
        assert ref.model == "test-model-1"
        assert ref.timestamp > 0
        assert ref.checksum is not None
        assert len(ref.checksum) == 64  # SHA256 hex length
        assert isinstance(ref.session_ids, list)
    
    @pytest.mark.asyncio
    async def test_create_image_reference_generates_thumbnail(self, workspace_dir, sample_image_base64):
        """Test that thumbnail file is actually created"""
        filename = "test_thumb.png"
        image_path = workspace_dir / filename
        image_bytes = base64.b64decode(sample_image_base64)
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        ref = await create_image_reference(
            image_data=sample_image_base64,
            filename=filename,
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Thumbnails are now kept in-memory as base64 (no file written by default)
        assert ref.thumbnail_base64 is not None and len(ref.thumbnail_base64) > 0
        # Legacy thumbnail_path is not written to disk by default
        assert ref.thumbnail_path == '' or ref.thumbnail_path is None
    
    @pytest.mark.asyncio
    async def test_create_image_reference_checksum_generation(self, workspace_dir, sample_image_base64):
        """Test that checksum is generated correctly"""
        filename = "test_checksum.png"
        image_path = workspace_dir / filename
        image_bytes = base64.b64decode(sample_image_base64)
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        ref = await create_image_reference(
            image_data=sample_image_base64,
            filename=filename,
            workspace_path=str(workspace_dir),
            prompt="test",
            model="test"
        )
        
        # Verify checksum is SHA256 hex (64 characters)
        assert ref.checksum is not None
        assert len(ref.checksum) == 64
        assert all(c in '0123456789abcdef' for c in ref.checksum)
        
        # Create another reference from same file, should have same checksum
        ref2 = await create_image_reference(
            image_data=sample_image_base64,
            filename=filename,
            workspace_path=str(workspace_dir),
            prompt="different prompt",
            model="different model"
        )
        
        assert ref.checksum == ref2.checksum

    @pytest.mark.asyncio
    async def test_link_and_unlink_session(self, workspace_dir, sample_image_base64):
        """Test linking and unlinking session IDs in the reference index"""
        service = ImageReferenceService(workspace_path=str(workspace_dir))
        ref = await service.create_reference(
            image_data=sample_image_base64,
            filename="linked.png",
            prompt="test",
            model="test",
            session_id="session-a",
            file_type="preview"
        )

        ok = await service.link_session(ref.image_id, "session-b")
        assert ok is True
        loaded = await service.get_reference(ref.image_id)
        assert loaded is not None
        assert set(loaded.session_ids or []) == {"session-a", "session-b"}

        result = await service.unlink_session("session-a")
        assert result["kept_refs"] >= 1
        loaded = await service.get_reference(ref.image_id)
        assert loaded is not None
        assert loaded.session_ids == ["session-b"]

    @pytest.mark.asyncio
    async def test_gc_removes_stale_preview_refs(self, workspace_dir):
        """Test garbage collection removes stale preview refs"""
        service = ImageReferenceService(workspace_path=str(workspace_dir))

        image_id = "stale-1"
        service._references[image_id] = {
            "image_id": image_id,
            "original_filename": "missing.png",
            "current_filename": "missing.png",
            "relative_path": "missing.png",
            "absolute_path": str(workspace_dir / "missing.png"),
            "mime_type": "image/png",
            "size_bytes": 0,
            "thumbnail_base64": "",
            "thumbnail_path": "",
            "prompt": "",
            "model": "",
            "timestamp": 0,
            "checksum": "",
            "file_type": "preview",
            "session_ids": ["session-x"],
        }
        service._write_index()

        result = await service.gc(max_age_days=1, now=1000)
        assert result["removed_refs"] == 1
        assert image_id not in service._references
    
    @pytest.mark.asyncio
    async def test_image_reference_service_initialization(self, workspace_dir):
        """Test ImageReferenceService initialization"""
        service = ImageReferenceService(workspace_path=str(workspace_dir))
        
        assert service.workspace_path == str(workspace_dir)
        assert service.thumbnails_dir.exists()
        assert service.thumbnails_dir.is_dir()
    
    @pytest.mark.asyncio
    async def test_image_reference_service_create_reference(self, workspace_dir, sample_image_base64):
        """Test ImageReferenceService.create_reference method"""
        service = ImageReferenceService(workspace_path=str(workspace_dir))
        
        filename = "service_test.png"
        image_path = workspace_dir / filename
        image_bytes = base64.b64decode(sample_image_base64)
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
        
        ref = await service.create_reference(
            image_data=sample_image_base64,
            filename=filename,
            prompt="service test",
            model="service-model"
        )
        
        assert ref is not None
        assert ref.image_id is not None
        assert ref.original_filename == filename
        assert ref.prompt == "service test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
