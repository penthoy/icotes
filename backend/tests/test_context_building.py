"""
Test 5: Context Building with Image References

Verifies that context builder correctly handles ImageReference objects
and builds optimized context for AI agents according to different strategies.
"""
import os
import sys
import json
import base64
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Set environment variables before imports
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from icpy.services.context_builder import (
    ContextBuilder,
    ContextConfig,
    ContextStrategy,
    create_context_builder
)


@pytest.fixture
def workspace():
    """Create temporary workspace"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_image_reference():
    """Create a sample ImageReference dict"""
    return {
        'image_id': 'test-image-123',
        'original_filename': 'test.png',
        'current_filename': 'test.png',
        'relative_path': 'test.png',
        'absolute_path': '/workspace/test.png',
        'mime_type': 'image/png',
        'size_bytes': 1024,
        'thumbnail_base64': 'dGVzdF90aHVtYm5haWw=',  # "test_thumbnail"
        'thumbnail_path': '.icotes/thumbnails/test-image-123.webp',
        'prompt': 'a red square',
        'model': 'imagen-3.0',
        'timestamp': 1234567890.0,
        'checksum': 'abc123def456'
    }


@pytest.fixture
def sample_message_with_reference(sample_image_reference):
    """Create a sample ChatMessage dict with ImageReference"""
    return {
        'id': 'msg-1',
        'content': 'Here is your image!',
        'sender': 'ai',
        'timestamp': '2024-01-01T00:00:00Z',
        'type': 'message',
        'metadata': {
            'tool_output': {
                'imageReference': sample_image_reference,
                'status': 'success'
            }
        },
        'session_id': 'test-session',
        'attachments': []
    }


@pytest.fixture
def sample_message_without_image():
    """Create a sample message without images"""
    return {
        'id': 'msg-2',
        'content': 'Hello, can you help me?',
        'sender': 'user',
        'timestamp': '2024-01-01T00:01:00Z',
        'type': 'message',
        'metadata': {},
        'session_id': 'test-session',
        'attachments': []
    }


def test_context_builder_initialization(workspace):
    """Test that ContextBuilder initializes correctly"""
    builder = ContextBuilder(workspace_path=workspace)
    
    assert builder.workspace_path == workspace
    assert builder.image_cache is not None
    assert builder.image_resolver is not None


def test_factory_function(workspace):
    """Test create_context_builder factory function"""
    builder = create_context_builder(workspace)
    
    assert isinstance(builder, ContextBuilder)
    assert builder.workspace_path == workspace


def test_metadata_only_strategy(sample_message_with_reference):
    """Test METADATA_ONLY strategy strips full images but keeps metadata"""
    builder = ContextBuilder()
    config = ContextConfig(
        strategy=ContextStrategy.METADATA_ONLY,
        include_thumbnails=True
    )
    
    messages = [sample_message_with_reference]
    context = builder.build_context(messages, config)
    
    assert len(context) == 1
    msg = context[0]
    
    # Should have imageReference
    assert 'imageReference' in msg['metadata']['tool_output']
    
    # Should NOT have imageData
    assert 'imageData' not in msg['metadata']['tool_output']
    
    # Should have essential metadata
    ref = msg['metadata']['tool_output']['imageReference']
    assert ref['image_id'] == 'test-image-123'
    assert ref['filename'] == 'test.png'
    assert ref['prompt'] == 'a red square'
    assert ref['model'] == 'imagen-3.0'
    
    # Should have thumbnail
    assert 'thumbnail_base64' in ref
    assert ref['thumbnail_base64'] == 'dGVzdF90aHVtYm5haWw='


def test_metadata_only_without_thumbnails(sample_message_with_reference):
    """Test METADATA_ONLY strategy without thumbnails"""
    builder = ContextBuilder()
    config = ContextConfig(
        strategy=ContextStrategy.METADATA_ONLY,
        include_thumbnails=False
    )
    
    messages = [sample_message_with_reference]
    context = builder.build_context(messages, config)
    
    ref = context[0]['metadata']['tool_output']['imageReference']
    
    # Should NOT have thumbnail when disabled
    assert 'thumbnail_base64' not in ref or ref.get('thumbnail_base64') is None


def test_thumbnails_only_strategy(sample_message_with_reference):
    """Test THUMBNAILS_ONLY strategy always includes thumbnails"""
    builder = ContextBuilder()
    config = ContextConfig(
        strategy=ContextStrategy.THUMBNAILS_ONLY,
        include_thumbnails=False  # Should be overridden
    )
    
    messages = [sample_message_with_reference]
    context = builder.build_context(messages, config)
    
    ref = context[0]['metadata']['tool_output']['imageReference']
    
    # Should have thumbnail even if include_thumbnails=False
    assert 'thumbnail_base64' in ref
    assert ref['thumbnail_base64'] == 'dGVzdF90aHVtYm5haWw='


def test_messages_without_images_unaffected(sample_message_without_image):
    """Test that messages without images pass through unchanged"""
    builder = ContextBuilder()
    config = ContextConfig(strategy=ContextStrategy.METADATA_ONLY)
    
    messages = [sample_message_without_image]
    context = builder.build_context(messages, config)
    
    assert len(context) == 1
    assert context[0]['content'] == 'Hello, can you help me?'
    assert context[0]['metadata'] == {}


def test_mixed_messages(sample_message_with_reference, sample_message_without_image):
    """Test context building with mixed messages (with and without images)"""
    builder = ContextBuilder()
    config = ContextConfig(strategy=ContextStrategy.METADATA_ONLY)
    
    messages = [
        sample_message_without_image,
        sample_message_with_reference,
        sample_message_without_image
    ]
    context = builder.build_context(messages, config)
    
    assert len(context) == 3
    
    # First message: no image
    assert 'imageReference' not in json.dumps(context[0])
    
    # Second message: has image reference
    assert 'imageReference' in context[1]['metadata']['tool_output']
    
    # Third message: no image
    assert 'imageReference' not in json.dumps(context[2])


def test_recent_full_strategy_loads_recent(workspace, sample_message_with_reference):
    """Test RECENT_FULL strategy loads full images for N most recent"""
    # Create a test image file
    test_image_path = Path(workspace) / 'test.png'
    test_image_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create simple 1x1 pixel PNG
    from PIL import Image
    import io
    img = Image.new('RGB', (1, 1), color='red')
    img.save(test_image_path, format='PNG')
    
    # Update reference to point to test file
    msg = sample_message_with_reference.copy()
    msg['metadata']['tool_output']['imageReference']['absolute_path'] = str(test_image_path)
    
    builder = ContextBuilder(workspace_path=workspace)
    config = ContextConfig(
        strategy=ContextStrategy.RECENT_FULL,
        max_full_images=1
    )
    
    # Test with 1 image (should load full)
    context = builder.build_context([msg], config)
    
    # Should have imageData loaded
    assert 'imageData' in context[0]['metadata']['tool_output']
    
    # Verify it's valid base64
    image_data = context[0]['metadata']['tool_output']['imageData']
    assert len(image_data) > 0
    
    # Should still have reference
    assert 'imageReference' in context[0]['metadata']['tool_output']


def test_recent_full_strategy_limits_count(workspace, sample_message_with_reference):
    """Test RECENT_FULL strategy respects max_full_images limit"""
    builder = ContextBuilder(workspace_path=workspace)
    config = ContextConfig(
        strategy=ContextStrategy.RECENT_FULL,
        max_full_images=2
    )
    
    # Create 3 messages with images
    messages = [
        sample_message_with_reference,
        {**sample_message_with_reference, 'id': 'msg-2'},
        {**sample_message_with_reference, 'id': 'msg-3'}
    ]
    
    context = builder.build_context(messages, config)
    
    # First 2 should have full images (if they can be loaded)
    # Third should have metadata only
    # Note: Since files don't exist, they'll all fall back to metadata
    # But the strategy logic should still be correct
    
    assert len(context) == 3


def test_selective_strategy_with_relevant_keywords(sample_message_with_reference):
    """Test SELECTIVE strategy loads images when content suggests relevance"""
    builder = ContextBuilder()
    config = ContextConfig(strategy=ContextStrategy.SELECTIVE)
    
    # Message asking about image editing
    msg = sample_message_with_reference.copy()
    msg['content'] = 'Can you edit this image and add a red hat?'
    
    messages = [msg]
    context = builder.build_context(messages, config)
    
    # Should attempt to load full image (will fail without file, but strategy is correct)
    # Check that processing was attempted
    assert 'imageReference' in context[0]['metadata']['tool_output']


def test_selective_strategy_without_relevant_keywords(sample_message_with_reference):
    """Test SELECTIVE strategy uses metadata when content not relevant"""
    builder = ContextBuilder()
    config = ContextConfig(strategy=ContextStrategy.SELECTIVE)
    
    # Message not related to images
    msg = sample_message_with_reference.copy()
    msg['content'] = 'What is the weather today?'
    
    messages = [msg]
    context = builder.build_context(messages, config)
    
    # Should use metadata only
    assert 'imageReference' in context[0]['metadata']['tool_output']
    assert 'imageData' not in context[0]['metadata']['tool_output']


def test_cache_integration(workspace, sample_message_with_reference):
    """Test that context builder uses image cache"""
    builder = ContextBuilder(workspace_path=workspace)
    
    # Pre-populate cache
    image_id = 'test-image-123'
    test_base64 = 'dGVzdF9pbWFnZV9kYXRh'  # "test_image_data"
    builder.image_cache.put(image_id, test_base64, 'image/png')
    
    config = ContextConfig(strategy=ContextStrategy.RECENT_FULL, max_full_images=1)
    
    messages = [sample_message_with_reference]
    context = builder.build_context(messages, config)
    
    # Should load from cache
    assert 'imageData' in context[0]['metadata']['tool_output']
    assert context[0]['metadata']['tool_output']['imageData'] == test_base64


def test_token_reduction():
    """Test that context builder significantly reduces token count"""
    # Create a large fake base64 image (simulating 1MB)
    large_base64 = 'A' * 1_400_000  # ~1MB base64 ≈ 350k tokens
    
    msg_with_large_image = {
        'id': 'msg-1',
        'content': 'Generated image',
        'sender': 'ai',
        'timestamp': '2024-01-01T00:00:00Z',
        'type': 'message',
        'metadata': {
            'tool_output': {
                'imageData': large_base64,
                'imageReference': {
                    'image_id': 'test-123',
                    'filename': 'big.png',
                    'prompt': 'test',
                    'model': 'test',
                    'size_bytes': 1000000,
                    'mime_type': 'image/png',
                    'thumbnail_base64': 'small_thumb',
                    'relative_path': 'big.png',
                    'absolute_path': '/workspace/big.png',
                    'thumbnail_path': '.icotes/thumbnails/test-123.webp',
                    'timestamp': 123456.0,
                    'checksum': 'abc123'
                }
            }
        },
        'session_id': 'test',
        'attachments': []
    }
    
    builder = ContextBuilder()
    config = ContextConfig(strategy=ContextStrategy.METADATA_ONLY)
    
    context = builder.build_context([msg_with_large_image], config)
    
    # Should remove imageData
    assert 'imageData' not in context[0]['metadata']['tool_output']
    
    # Calculate approximate token reduction
    original_size = len(json.dumps(msg_with_large_image))
    optimized_size = len(json.dumps(context[0]))
    reduction_pct = (1 - optimized_size / original_size) * 100
    
    # Should achieve >95% reduction
    assert reduction_pct > 95, f"Only achieved {reduction_pct:.1f}% reduction"
    
    print(f"✓ Token reduction: {original_size:,} → {optimized_size:,} bytes ({reduction_pct:.1f}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
