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
            checksum="abc123"
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
            checksum="abc123"
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
            'checksum': "abc123"
        }
        
        ref = ImageReference.from_dict(data)
        
        assert ref.image_id == "test-123"
        assert ref.original_filename == "test.png"
        assert ref.prompt == "test prompt"
    
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
