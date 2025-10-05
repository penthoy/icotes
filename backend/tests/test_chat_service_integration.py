"""
Test integration of Phase 1 image reference system with chat_service.py
"""
import os
import sys
import json
import base64
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Set environment variables before imports
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from icpy.services.chat_service import ChatService, ChatMessage


@pytest.fixture
def workspace():
    """Create temporary workspace"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_image_base64():
    """Create a small test image as base64"""
    from PIL import Image
    import io
    
    # Create 100x100 red square
    img = Image.new('RGB', (100, 100), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.read()).decode('utf-8')


@pytest.mark.asyncio
async def test_imagedata_converted_to_reference_on_storage(workspace, sample_image_base64):
    """Test that imageData is automatically converted to ImageReference when storing"""
    
    # Set workspace via environment variable
    os.environ['WORKSPACE_ROOT'] = workspace
    os.environ['CHAT_BUFFERED_STORE'] = '0'  # Disable buffering for immediate writes
    
    # Create chat service with test workspace
    chat_service = ChatService()
    
    # Create a message with imageData in metadata (mimicking NanoBananaAgent output)
    from icpy.services.chat_service import MessageSender
    message = ChatMessage(
        id="msg-1",
        content="Here is your generated image!",
        sender=MessageSender.AI,
        timestamp="2024-01-01T00:00:00Z",
        session_id="test-session",
        metadata={
            "tool_output": {
                "imageData": sample_image_base64,
                "filePath": "test_image.png",
                "prompt": "a red square",
                "model": "imagen-3.0",
                "mimeType": "image/png"
            }
        }
    )
    
    # Store the message
    await chat_service._store_message(message)
    
    # Read back from JSONL (test mode uses different path structure)
    # In test mode, files go to /.icotes_test_<uuid>/chat_history/
    test_workspace_dirs = list(Path(workspace).glob('.icotes_test_*/chat_history'))
    assert len(test_workspace_dirs) > 0, f"No test workspace found in {workspace}"
    
    session_file = test_workspace_dirs[0] / "test-session.jsonl"
    assert session_file.exists(), f"Session file should be created at {session_file}"
    
    with open(session_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        assert len(lines) == 1, "Should have one message"
        
        stored_message = json.loads(lines[0])
        tool_output = stored_message['metadata']['tool_output']
        
        # Verify conversion happened
        assert 'imageReference' in tool_output, "Should have imageReference"
        assert 'imageData' not in tool_output, "Should NOT have imageData"
        
        # Verify reference structure
        ref = tool_output['imageReference']
        assert ref['image_id'], "Should have image_id"
        assert ref['thumbnail_base64'], "Should have thumbnail"
        assert ref['relative_path'], "Should have relative_path"
        assert ref['checksum'], "Should have checksum"
        assert ref['prompt'] == "a red square", "Should preserve prompt"
        assert ref['model'] == "imagen-3.0", "Should preserve model"
        
        # Verify thumbnail is much smaller than original
        thumbnail_size = len(ref['thumbnail_base64'])
        original_size = len(sample_image_base64)
        reduction = (1 - thumbnail_size / original_size) * 100
        
        assert reduction > 50, f"Thumbnail should be at least 50% smaller (got {reduction:.1f}%)"
        
        print(f"✓ Size reduction: {original_size} → {thumbnail_size} bytes ({reduction:.1f}%)")


@pytest.mark.asyncio
async def test_original_image_saved_to_workspace(workspace, sample_image_base64):
    """Test that original image is saved to workspace"""
    
    os.environ['WORKSPACE_ROOT'] = workspace
    os.environ['CHAT_BUFFERED_STORE'] = '0'
    
    chat_service = ChatService()
    
    from icpy.services.chat_service import MessageSender
    message = ChatMessage(
        id="msg-2",
        content="Image generated",
        sender=MessageSender.AI,
        timestamp="2024-01-01T00:00:00Z",
        session_id="test-session",
        metadata={
            "tool_output": {
                "imageData": sample_image_base64,
                "filePath": "my_image.png",
                "prompt": "test",
                "model": "test-model",
                "mimeType": "image/png"
            }
        }
    )
    
    await chat_service._store_message(message)
    
    # Check original image exists in workspace (in the test workspace)
    test_workspace_dirs = list(Path(workspace).glob('.icotes_test_*'))
    assert len(test_workspace_dirs) > 0, "Test workspace should be created"
    
    workspace_path = test_workspace_dirs[0]
    image_files = list(workspace_path.glob("my_image.png"))
    
    assert len(image_files) > 0, "Original image should be saved to workspace"
    
    # Verify it's a valid PNG
    from PIL import Image
    img = Image.open(image_files[0])
    assert img.format == 'PNG', "Should be a PNG image"
    assert img.size == (100, 100), "Should preserve original dimensions"


@pytest.mark.asyncio
async def test_thumbnail_created_on_disk(workspace, sample_image_base64):
    """Test that thumbnail is created in .icotes/thumbnails/"""
    
    os.environ['WORKSPACE_ROOT'] = workspace
    os.environ['CHAT_BUFFERED_STORE'] = '0'
    
    chat_service = ChatService()
    
    from icpy.services.chat_service import MessageSender
    message = ChatMessage(
        id="msg-3",
        content="Image generated",
        sender=MessageSender.AI,
        timestamp="2024-01-01T00:00:00Z",
        session_id="test-session",
        metadata={
            "tool_output": {
                "imageData": sample_image_base64,
                "filePath": "test.png",
                "prompt": "test",
                "model": "test-model",
                "mimeType": "image/png"
            }
        }
    )
    
    await chat_service._store_message(message)
    
    # Check thumbnail directory exists (in test workspace)
    test_workspace_dirs = list(Path(workspace).glob('.icotes_test_*'))
    workspace_path = test_workspace_dirs[0]
    
    thumbnail_dir = workspace_path / ".icotes" / "thumbnails"
    assert thumbnail_dir.exists(), f"Thumbnail directory should be created at {thumbnail_dir}"
    
    # Check thumbnail file exists
    thumbnails = list(thumbnail_dir.glob("*.webp"))
    assert len(thumbnails) > 0, "Thumbnail should be created"
    
    # Verify it's a valid WebP and small
    from PIL import Image
    thumb = Image.open(thumbnails[0])
    assert thumb.format == 'WEBP', "Thumbnail should be WebP format"
    assert max(thumb.size) <= 128, "Thumbnail should be max 128px"
    
    # Check file size
    thumb_size = thumbnails[0].stat().st_size
    assert thumb_size < 10 * 1024, "Thumbnail should be under 10KB"


@pytest.mark.asyncio
async def test_image_cached_in_memory(workspace, sample_image_base64):
    """Test that base64 image is cached in memory for immediate access"""
    
    os.environ['WORKSPACE_ROOT'] = workspace
    os.environ['CHAT_BUFFERED_STORE'] = '0'
    
    chat_service = ChatService()
    
    from icpy.services.chat_service import MessageSender
    message = ChatMessage(
        id="msg-4",
        content="Image generated",
        sender=MessageSender.AI,
        timestamp="2024-01-01T00:00:00Z",
        session_id="test-session",
        metadata={
            "tool_output": {
                "imageData": sample_image_base64,
                "filePath": "cached.png",
                "prompt": "test",
                "model": "test-model",
                "mimeType": "image/png"
            }
        }
    )
    
    await chat_service._store_message(message)
    
    # Read back the image_id from storage
    test_workspace_dirs = list(Path(workspace).glob('.icotes_test_*/chat_history'))
    session_file = test_workspace_dirs[0] / "test-session.jsonl"
    
    with open(session_file, 'r') as f:
        stored = json.loads(f.read())
        image_id = stored['metadata']['tool_output']['imageReference']['image_id']
    
    # Check if cached
    cached = chat_service.image_cache.get(image_id)
    assert cached is not None, "Image should be cached in memory"
    assert cached == sample_image_base64, "Cached data should match original"


@pytest.mark.asyncio
async def test_no_conversion_if_no_imagedata(workspace):
    """Test that messages without imageData are stored normally"""
    
    os.environ['WORKSPACE_ROOT'] = workspace
    os.environ['CHAT_BUFFERED_STORE'] = '0'
    
    chat_service = ChatService()
    
    from icpy.services.chat_service import MessageSender
    message = ChatMessage(
        id="msg-5",
        content="Hello, can you generate an image?",
        sender=MessageSender.USER,
        timestamp="2024-01-01T00:00:00Z",
        session_id="test-session"
    )
    
    await chat_service._store_message(message)
    
    # Read back
    test_workspace_dirs = list(Path(workspace).glob('.icotes_test_*/chat_history'))
    assert len(test_workspace_dirs) > 0, f"No test workspace found in {workspace}"
    
    session_file = test_workspace_dirs[0] / "test-session.jsonl"
    assert session_file.exists(), f"Session file should be created at {session_file}"
    
    with open(session_file, 'r') as f:
        stored = json.loads(f.read())
        
        assert stored['content'] == "Hello, can you generate an image?"
        assert stored['sender'] == "user"
        # Should not have any image references
        assert 'imageReference' not in json.dumps(stored)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
